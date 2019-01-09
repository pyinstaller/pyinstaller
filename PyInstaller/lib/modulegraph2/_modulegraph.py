"""
The actual graph
"""
import os
import ast
import sys
import collections
import importlib
from typing import (
    Optional,
    Tuple,
    Union,
    TextIO,
    Deque,
    Callable,
    Dict,
    List,
    Iterable,
    Iterator,
    Set,
)

from ._objectgraph import ObjectGraph
from ._nodes import (
    BaseNode,
    Script,
    AliasNode,
    ExcludedModule,
    MissingModule,
    Package,
    NamespacePackage,
)
from ._packages import PyPIDistribution
from ._graphbuilder import node_for_spec
from ._implies import Alias  # XXX
from ._ast_tools import extract_ast_info
from ._depinfo import DependencyInfo, merged_depinfo

from . import _ast_tools, _bytecode_tools


def full_name(import_name: str, package: Optional[str]):
    """
    Return the fully qualified module name for an imported
    name, resolving relative imports if needed.
    """
    # XXX: Nicer exceptions (esp. second one)
    if import_name.startswith("."):
        if package is None:
            raise ValueError((import_name, package))

        while import_name.startswith(".."):
            package, _ = split_package(package)
            if package is None:
                raise ValueError((import_name, package))
            import_name = import_name[1:]

        return f"{package}{import_name}"

    return import_name


def split_package(name: str) -> Tuple[Optional[str], str]:
    """
    Return (package, name) given a fully qualified module name

    package is ``None`` for toplevel modules
    """
    if not isinstance(name, str):
        raise TypeError(f"Expected 'str', got instance of {type(name)!r}")
    if not name:
        raise ValueError(f"Invalid module name {name!r}")

    name_abs = name.lstrip(".")
    dots = len(name) - len(name_abs)
    if not name_abs or ".." in name_abs:
        raise ValueError(f"Invalid module name {name!r}")

    package, _, name = name_abs.rpartition(".")
    if dots:
        package = ("." * dots) + package

    return (package if package is not "" else None), name


class ModuleGraph(ObjectGraph[BaseNode]):
    # Redesign of modulegraph.modulegraph.ModuleGraph
    # Gloal:
    # - minimal, but complete interface
    # - fully tested
    # - Python 3 only, use importlib and modern features
    #
    # XXX: Detect if "from mod import name" access a submodule
    #      or a global name.
    _path: List[str]
    _post_processing: List[Callable[["ModuleGraph", BaseNode], None]]
    _work_q: Deque[Tuple[Callable, tuple]]
    _global_lazy_nodes: Dict[str, Optional[Alias]]
    _distribution_lazy_nodes: Dict[str, Dict[str, Optional[Alias]]]
    _finished: Set[str]
    _finished_callbacks: Dict[str, Tuple[Callable, tuple]]

    def __init__(self, *, path: List[str] = None):
        super().__init__()
        self._path = path if path is not None else sys.path
        self._post_processing = []
        self._work_q = collections.deque()

        self._global_lazy_nodes = {}
        self._distribution_lazy_nodes = {}

        self._finished = set()
        self._finished_callbacks = {}

        # Reference to __main__ cannot be valid when multip scripts
        # are added to the graph, just ignore this module for now.
        self._global_lazy_nodes["__main__"] = None

    #
    # Querying
    #
    def distributions(self, reachable: bool = True) -> Iterator[PyPIDistribution]:
        """
        Yield all distributions used in the graph.

        If reachable is True (default) this reports only on distributions
        used by nodes reachable from one of the graph roots, otherwise
        this reports on distributions used by any root.
        """
        seen: Set[str] = set()
        for node in self.iter_graph() if reachable else self.nodes():
            if isinstance(node, PyPIDistribution):
                if node.identifier not in seen:
                    seen.add(node.identifier)
                    yield node

    #
    # Reporting:
    #
    def report(self, stream: TextIO = sys.stdout) -> None:
        print(file=stream)
        print("%-15s %-25s %s" % ("Class", "Name", "File"), file=stream)
        print("%-15s %-25s %s" % ("-----", "----", "----"), file=stream)
        for m in sorted(self.iter_graph(), key=lambda n: n.identifier):
            print(
                "%-15s %-25s %s" % (type(m).__name__, m.identifier, m.filename or ""),
                file=stream,
            )

    #
    # Adding to the graph:
    #

    def add_script(self, script_path: os.PathLike) -> Script:
        """ Add a script to the module graph and process imports """
        node = self._load_script(script_path)
        self.add_root(node)
        self._run_q()
        return node

    def add_module(self, module_name: str) -> BaseNode:
        node = self._load_module(module_name)
        self.add_root(node)
        self._run_q()
        return node

    #
    # Hooks
    #

    def import_module(self, module: BaseNode, import_name: str) -> BaseNode:
        # Explicitly add edge to the graph, for use by hooks
        # parent, _ = split_package(self.find_node(module).identifier)
        # return self._import_module(module, parent=parent)
        ...

    def _run_post_processing(self, node: BaseNode) -> None:
        for hook in self._post_processing:
            hook(self, node)

        self._finished.add(node.identifier)

        if node.identifier in self._finished_callbacks:
            callable, args = self._finished_callbacks.pop(node.identifier)
            callable(*args)

    def add_post_processing_hook(
        self, hook: Callable[["ModuleGraph", BaseNode], None]
    ) -> None:
        """
        Run 'hook(self, node)' after *node* is fully processed.
        """
        self._post_processing.append(hook)

    #
    # Internal: building the graph
    #

    def _run_q(self) -> None:
        while self._work_q:
            func, args = self._work_q.popleft()
            func(*args)

    # def _load_implies_for_distribution(self, distribution: PyPIDistribution):
    #    """
    #    Load distribution specific implies into the global implies table
    #    """
    #    if distribution.name in self._distribution_lazy_nodes:
    #        lazy_nodes = self._distribution_lazy_nodes.pop(distribution.name)
    #        self._global_lazy_nodes.update(lazy_nodes)

    def _implied_references(self, full_name: str) -> Optional[BaseNode]:
        # XXX: This recurses...
        assert self.find_node(full_name) is None
        node: BaseNode

        if full_name in self._global_lazy_nodes:
            implied = self._global_lazy_nodes.pop(full_name)

            if implied is None:
                node = ExcludedModule(full_name)
                self.add_node(node)
                return None

            elif isinstance(implied, Alias):
                node = AliasNode(full_name, implied)
                other = self._load_module(implied)
                self.add_edge(node, other, merge_attributes=merged_depinfo)
                return node

            else:
                # XXX: _load_module does not load enclosing package!
                node = self._load_module(full_name)
                for ref in implied:
                    other = self._load_module(ref)
                    self.add_edge(node, other, merge_attributes=merged_depinfo)

                return node

        else:
            return None

    def _load_module(self, module_name: str) -> BaseNode:
        # module_name must be an absolute module name
        # print("load_module", module_name)
        node = self.find_node(module_name)
        assert node is None

        spec = importlib.util.find_spec(module_name)
        if spec is None:
            node = MissingModule(module_name)
            self.add_node(node)
            return node

        node, imports = node_for_spec(spec, self._path)
        if node.name != module_name:
            # Some kind of alias
            alias_node = AliasNode(module_name, node.name)
            self.add_node(alias_node)
            if self.find_node(node) is None:
                self.add_node(node)
                self._process_import_list(node, imports)
            self.add_edge(alias_node, node, merge_attributes=merged_depinfo)
            return alias_node

        self.add_node(node)
        self._process_import_list(node, imports)

        return node

    def _load_script(self, script_path: os.PathLike) -> Script:
        node = Script(os.fspath(script_path))  # XXX
        self.add_node(node)

        with open(script_path, "rb") as fp:
            source_bytes = fp.read()

        source_code = importlib.util.decode_source(source_bytes)
        ast_node = compile(
            source_code,
            os.fspath(script_path),
            "exec",
            flags=ast.PyCF_ONLY_AST,
            dont_inherit=True,
        )
        imports = extract_ast_info(ast_node)

        self._process_import_list(node, imports)
        return node

    def _process_import_list(self, node: BaseNode, imports: Iterable):
        have_imports = False

        for info in imports:
            self._work_q.append((self._process_import, (node, info)))
            have_imports = True

        if have_imports:
            self._work_q.append((self._run_post_processing, (node,)))
        else:
            self._run_post_processing(node)

    def _find_or_load(self, module_name: str) -> BaseNode:
        node = self.find_node(module_name)
        if node is None:
            node = self._implied_references(module_name)
        if node is None:
            node = self._load_module(module_name)

        assert node is not None

        return node

    def _import_containing_package(self, module_name: str) -> Optional[BaseNode]:
        node: BaseNode

        containing_package, _ = split_package(module_name)
        if containing_package is None:
            return None

        parent = self.find_node(containing_package)
        if parent is not None:
            return parent

        parent = self._import_containing_package(containing_package)
        if isinstance(parent, MissingModule):
            node = MissingModule(containing_package)
            self.add_node(node)

        else:
            node = self._find_or_load(containing_package)

        if parent is not None:
            self.add_edge(node, parent, merge_attributes=merged_depinfo)
        return node

    def _process_import(
        self,
        importing_module: BaseNode,
        import_info: Union[_bytecode_tools.ImportInfo, _ast_tools.ImportInfo],
    ):
        # print("_process_import", import_info.import_module)
        if import_info.import_level == 0:
            # Global import
            node = self.find_node(import_info.import_module)
            if node is None:
                parent_node = self._import_containing_package(import_info.import_module)
                if isinstance(parent_node, MissingModule):
                    node = MissingModule(import_info.import_module)
                    self.add_node(node)

                else:
                    node = self._find_or_load(import_info.import_module)

                if parent_node is not None:
                    self.add_edge(node, parent_node, merge_attributes=merged_depinfo)

            assert node is not None

            self.add_edge(
                importing_module,
                node,
                DependencyInfo(import_info.is_optional, False),
                merge_attributes=merged_depinfo,
            )

            for nm in import_info.import_names:
                if isinstance(node, (Package, NamespacePackage)):
                    # XXX: Find a way to avoid creating a MissingModule name when it isn't
                    # actually necessary (those currently end up as nodes that aren't
                    # connected to the graph roots)
                    subnode = self._find_or_load(f"{import_info.import_module}.{nm}")
                    if isinstance(subnode, MissingModule):
                        if nm in node.globals_written:
                            # Name exists, but is not a module, don't add edge
                            # to the "missing" node
                            continue
                    self.add_edge(subnode, node, merge_attributes=merged_depinfo)
                    self.add_edge(
                        importing_module,
                        subnode,
                        DependencyInfo(import_info.is_optional, True),
                        merge_attributes=merged_depinfo,
                    )
                # else:
                #    Node is not a package, therefore "from node import a" cannot
                #    refer to a submodule.

                # XXX: Should this

            if import_info.star_import:
                # Star import
                if isinstance(node, Package):
                    # Implicit namespace packages (node type NamespacePackage)
                    # are ignored here, those don't have an __init__.py that
                    # can set globals.
                    #
                    # This is not 100% correct though, importing sub modules
                    # will update the package __dict__ and will affect the
                    # names that 'from package import *' will import. That
                    # effect is ignored by modulegraph though (and no sane code
                    # should rely on that action-at-a-distance behaviour).

                    if node.identifier in self._finished:
                        importing_module.globals_written.update(node.globals_written)

                    else:
                        self._finished_callbacks[node.identifier] = (
                            lambda: importing_module.globals_written.update(
                                node.globals_written
                            ),
                            (),
                        )
                # Else:
                #   Node is not a package, therefore "from node import *" cannot
                #   refer to submodule.

            # XXX: This return statement is here to make coverage.py happy, otherwise
            # it gets confused by the bytecode that CPython 3.7.2 generates.
            return

        else:
            # Relative import
            ...
