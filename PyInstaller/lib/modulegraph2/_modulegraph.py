"""
The actual graph
"""
import os
import ast
import sys
import collections
import importlib
import functools
import operator
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

from ._callback_list import CallbackList
from ._objectgraph import ObjectGraph
from ._nodes import (
    BaseNode,
    Module,
    Script,
    AliasNode,
    ExcludedModule,
    MissingModule,
    Package,
    NamespacePackage,
    InvalidRelativeImport,
)
from ._packages import PyPIDistribution
from ._graphbuilder import node_for_spec
from ._implies import Alias  # XXX
from ._ast_tools import extract_ast_info
from ._depinfo import DependencyInfo, from_importinfo
from ._depproc import DependentProcessor
from ._importinfo import ImportInfo


def full_name(import_name: str, package: Optional[str]):
    """
    Return the fully qualified module name for an imported
    name, resolving relative imports if needed.
    """
    # XXX: Nicer exceptions (esp. second one)
    # XXX: There is an importlib API for this!
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


ProcessingCallback = Callable[["ModuleGraph", BaseNode], None]

DEFAULT_DEPENDENCY = DependencyInfo(False, True, False, None)


class ModuleGraph(ObjectGraph[BaseNode, Set[DependencyInfo]]):
    # Redesign of modulegraph.modulegraph.ModuleGraph
    # Gloal:
    # - minimal, but complete interface
    # - fully tested
    # - Python 3 only, use importlib and modern features
    #
    # XXX: Detect if "from mod import name" access a submodule
    #      or a global name.
    _path: List[str]
    _post_processing: CallbackList[ProcessingCallback]
    _work_q: Deque[Tuple[Callable, tuple]]
    _global_lazy_nodes: Dict[str, Optional[Alias]]

    _depproc: DependentProcessor

    def __init__(self, *, path: List[str] = None):
        # XXX: AFAIK importlib doesn't allow maintaning separate
        # state, but more code inspection is needed. If it turns
        # out there is no clean way to work with an alternate path
        # the 'path' parameter will be removed (including any code
        # related to it). Note that using an alternate path
        # requires code changes anyway.
        #
        # XXX: Add init parameters to control if std. hooks are
        # used (in particular the stdlib implies and support for
        # virtual environments)
        super().__init__()
        self._path = path if path is not None else sys.path
        self._post_processing = CallbackList()
        self._work_q = collections.deque()
        self._depproc = DependentProcessor()

        self._global_lazy_nodes = {}

        # Reference to __main__ cannot be valid when multip scripts
        # are added to the graph, just ignore this module for now.
        # self._global_lazy_nodes["__main__"] = None

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
            if isinstance(node.distribution, PyPIDistribution):
                if node.distribution.identifier not in seen:
                    seen.add(node.distribution.identifier)
                    yield node.distribution

    #
    # Reporting:
    #
    def report(self, stream: TextIO = sys.stdout) -> None:
        print(file=stream)
        print("%-15s %-25s %s" % ("Class", "Name", "File"), file=stream)
        print("%-15s %-25s %s" % ("-----", "----", "----"), file=stream)
        for m in sorted(self.iter_graph(), key=operator.attrgetter("identifier")):
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
        """
        Import 'import_name' and add an edge from 'module' to 'import_name'

        This is an API to be used by hooks. The graph is not fully updated
        after calling this method.
        """
        node = self._load_module(import_name)
        self.add_edge(module, node, {DEFAULT_DEPENDENCY}, merge_attributes=operator.or_)
        return node

    def _run_post_processing(self, node: BaseNode) -> None:
        self._post_processing(self, node)
        self._depproc.dec_depcount(node)

        # XXX: Need to redesign the finished state and callbacks:
        # - A node is "finished" at this point unless it has 'star_import'
        # - With star_import we need to wait for the the modules we
        #   import from to be finished.
        # - When this node is finished check all nodes reachable over
        #   incoming edges to see if those are now finished.
        # - This needs the following state:
        #   a) Are all import statements processed (_process_import called)
        #   b) List of unprocessed from (* or namelist) imports
        #   { destination_node:  ipmorting_node, Optional[namelist] }
        #   -> This likely doens't need full callback support.
        # - State should be stored outside of the nodes itself to keep the
        #   interface clean.
        # - Should take care here to avoid deep recursion (use a work_q like
        #   we do elsewhere)

    def add_post_processing_hook(self, hook: ProcessingCallback) -> None:
        """
        Run 'hook(self, node)' after *node* is fully processed.
        """
        self._post_processing.add(hook)

    #
    # Internal: building the graph
    #

    def _run_q(self) -> None:
        while self._work_q or self._depproc.have_finished_work():
            if self._work_q:
                func, args = self._work_q.popleft()
                func(*args)

            if self._depproc.have_finished_work():
                self._depproc.process_finished_nodes()

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
                self.add_edge(
                    node, other, {DEFAULT_DEPENDENCY}, merge_attributes=operator.or_
                )
                return node

            else:
                # XXX: _load_module does not load enclosing package!
                node = self._load_module(full_name)
                for ref in implied:
                    other = self._load_module(ref)
                    self.add_edge(
                        node, other, {DEFAULT_DEPENDENCY}, merge_attributes=operator.or_
                    )

                return node

        else:
            return None

    def _load_module(self, module_name: str) -> BaseNode:
        # XXX: This doesn't load parent packages, while a number
        # of callers assume this will.

        # module_name must be an absolute module name
        node = self.find_node(module_name)
        assert node is None, module_name

        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                node = MissingModule(module_name)
                self.add_node(node)
                return node

        except ImportError:
            node = MissingModule(module_name)
            self.add_node(node)
            return node

        node, imports = node_for_spec(spec, self._path)
        if node.name != module_name:
            # Some kind of alias
            # XXX: Need to determine when this can happen, to
            # reproduce in a test. Code as added when building a
            # graph with "real" data.
            alias_node = AliasNode(module_name, node.name)
            self.add_node(alias_node)
            if self.find_node(node) is None:
                self.add_node(node)
                self._process_import_list(node, imports)
            self.add_edge(
                alias_node, node, {DEFAULT_DEPENDENCY}, merge_attributes=operator.or_
            )
            return alias_node

        self.add_node(node)
        self._process_import_list(node, imports)

        return node

    def _load_script(self, script_path: os.PathLike) -> Script:
        # XXX: What should happen when "script_path" does not exist
        # 1) Create a MissingScript node
        # 2) Raise a nice exception (without updating the graph)
        #
        # We currently do (2) but I'm not sure if that's the right
        # API.

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

        node = Script(os.fspath(script_path))
        self.add_node(node)
        self._process_import_list(node, imports)
        return node

    def _process_import_list(
        self, node: BaseNode, imports: Iterable
    ):  # XXX: MyPy annotation
        """
        Schedule processing of all *imports* and the finalizer when
        that's done.
        """
        have_imports = False

        for info in imports:
            if info.import_names or info.star_import:
                self._depproc.inc_depcount(node)

            self._work_q.append((self._process_import, (node, info)))
            have_imports = True

        self._depproc.inc_depcount(node)
        if have_imports:
            self._work_q.append((self._run_post_processing, (node,)))
        else:
            self._run_post_processing(node)

    def _find_or_load(self, module_name: str) -> BaseNode:
        # XXX: Name
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
            self.add_edge(
                node, parent, {DEFAULT_DEPENDENCY}, merge_attributes=operator.or_
            )
        return node

    def _process_import(self, importing_module: BaseNode, import_info: ImportInfo):
        node: Optional[BaseNode]

        # print("_process_import", import_info.import_module)
        if import_info.import_level == 0:
            # Absolute import
            absolute_name = import_info.import_module

            node = self.find_node(absolute_name)
            if node is None:
                parent_node = self._import_containing_package(absolute_name)
                if isinstance(parent_node, MissingModule):
                    node = MissingModule(absolute_name)
                    self.add_node(node)

                else:
                    node = self._find_or_load(absolute_name)

                if parent_node is not None:
                    self.add_edge(
                        node,
                        parent_node,
                        {DEFAULT_DEPENDENCY},
                        merge_attributes=operator.or_,
                    )

            assert node is not None

            self.add_edge(
                importing_module,
                node,
                {from_importinfo(import_info, False, None)},
                merge_attributes=operator.or_,
            )

            if import_info.import_names or import_info.star_import:
                self._depproc.wait_for(
                    importing_module,
                    node,
                    functools.partial(
                        _process_namelist, graph=self, import_info=import_info
                    ),
                )

        else:
            # Relative import, calculate the absolute name
            bits = importing_module.identifier.rsplit(".", import_info.import_level)
            if len(bits) < import_info.import_level + 1:
                # Invalid relative import: points to outside of a top-level package
                node = InvalidRelativeImport(
                    ("." * import_info.import_level) + import_info.import_module
                )
                self.add_node(node)
                self.add_edge(
                    importing_module,
                    node,
                    {from_importinfo(import_info, False, None)},
                    merge_attributes=operator.or_,
                )

                # Ignore the import_names and star_import attributes of import_info, that would
                # just add more InvalidRelativeImport nodes.
                return

            prefix = f"{bits[0]}.{import_info.import_module}".rstrip(".")

            for nm in import_info.import_names:
                absolute_name = f"{prefix}.{nm}"

                node = self.find_node(absolute_name)
                if node is None:
                    parent_node = self._import_containing_package(absolute_name)
                    if isinstance(parent_node, MissingModule):
                        node = MissingModule(absolute_name)
                        self.add_node(node)

                    else:
                        node = self._find_or_load(absolute_name)

                    if parent_node is not None:
                        self.add_edge(
                            node,
                            parent_node,
                            {DEFAULT_DEPENDENCY},
                            merge_attributes=operator.or_,
                        )

                assert node is not None

                self.add_edge(
                    importing_module,
                    node,
                    {from_importinfo(import_info, False, None)},
                    merge_attributes=operator.or_,
                )

        # See python issue #2506: The peephole optimizer confuses coverage.py
        # w.r.t. coverage of the previous statement unless the return statement
        # below is present.
        return


def _process_namelist(
    importing_module: Union[Module, Package],
    imported_module: BaseNode,
    graph: ModuleGraph,
    import_info: ImportInfo,
):
    assert isinstance(importing_module, (Module, Package))
    if import_info.star_import:
        if isinstance(imported_module, (Package, Module)):
            importing_module.globals_written.update(imported_module.globals_written)

    else:
        importing_module.globals_written.update(import_info.import_names)

        if import_info.import_names and isinstance(
            imported_module, (Package, NamespacePackage)
        ):
            for nm in import_info.import_names:
                subnode = graph._find_or_load(f"{import_info.import_module}.{nm}")
                # XXX: graph._find_or_load alternative that doesn't create MissingModule
                if isinstance(subnode, MissingModule):
                    if nm in imported_module.globals_written:
                        # Name exists, but is not a module, don't add edge
                        # to the "missing" node

                        # Check if the imported name is actually some other imported
                        # module.
                        for ed_set, tgt in graph.outgoing(imported_module):
                            # ed = cast(Optional[DependencyInfo], ed)
                            if (
                                any(nm == ed.imported_as for ed in ed_set)
                                or tgt.identifier == nm
                            ):
                                graph.add_edge(
                                    importing_module,
                                    tgt,
                                    {from_importinfo(import_info, True, None)},
                                )
                                break
                        continue

                graph.add_edge(
                    subnode,
                    imported_module,
                    {DEFAULT_DEPENDENCY},
                    merge_attributes=operator.or_,
                )
                graph.add_edge(
                    importing_module,
                    subnode,
                    {from_importinfo(import_info, True, nm)},
                    merge_attributes=operator.or_,
                )
                # else:
                #    Node is not a package, therefore "from node import a" cannot
                #    refer to a submodule.

                # XXX: Should this

    graph._depproc.dec_depcount(importing_module)
