"""
This module contains the definition of the ModuleGraph class.
"""
import ast
import functools
import importlib
import operator
import os
import sys
from types import ModuleType
from typing import (
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    TextIO,
    Tuple,
    Union,
    cast,
)

from objectgraph import ObjectGraph

from ._ast_tools import extract_ast_info
from ._callback_list import CallbackList, FirstNotNone
from ._delayed_call import DelayedCaller
from ._depinfo import DependencyInfo, from_importinfo
from ._distributions import PyPIDistribution
from ._graphbuilder import SIX_MOVES_TO, node_for_spec, relative_package
from ._implies import STDLIB_IMPLIES, Alias, ImpliesValueType
from ._importinfo import ImportInfo
from ._nodes import (
    AliasNode,
    BaseNode,
    ExcludedModule,
    InvalidRelativeImport,
    MissingModule,
    Module,
    NamespacePackage,
    Package,
    Script,
)
from ._swig_support import swig_missing_hook


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
MissingCallback = Callable[["ModuleGraph", Optional[BaseNode], str], Optional[BaseNode]]

DEFAULT_DEPENDENCY = DependencyInfo(False, True, False, None)


class FakePackage:
    """
    Instances of these can be used to represent a fake
    package in :data:`sys.modules`.

    Used as a workaround to fetch information about modules
    in packages when the package itself cannot be imported
    for some reason (for example due to having a SyntaxError
    in the module ``__init__.py`` file).
    """
    def __init__(self, path: List[str]):
        """
        Create a new instance.

        Args:
           path: The search path for sub modules
        """
        self.__path__ = path


class ModuleGraph(ObjectGraph[BaseNode, DependencyInfo]):
    """
    Class representing the dependency graph between a collection
    of python modules and scripts.

    The roots of the graph are those nodes that are added to the
    graph using :meth:`add_script() <ModuleGraph.add_script>` and
    :meth:`add_module() <ModuleGraph.add_module>`.
    """
    _post_processing: CallbackList[ProcessingCallback]
    _missing_hook: FirstNotNone[MissingCallback]
    _work_stack: List[Tuple[Callable, tuple]]
    _global_lazy_nodes: Dict[str, ImpliesValueType]
    _delayed: DelayedCaller

    def __init__(
        self, *, use_stdlib_implies: bool = True, use_builtin_hooks: bool = True
    ):
        super().__init__()
        self._post_processing = CallbackList()
        self._missing_hook = FirstNotNone()
        self._work_stack = []
        self._delayed = DelayedCaller()

        self._global_lazy_nodes = {}

        # Reference to __main__ cannot be valid when multip scripts
        # are added to the graph, just ignore this module for now.
        self._global_lazy_nodes["__main__"] = None

        if use_stdlib_implies:
            self.add_implies(STDLIB_IMPLIES)

        if use_builtin_hooks:
            self.add_missing_hook(swig_missing_hook)

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
    def report(self, file: TextIO = sys.stdout) -> None:
        """
        Print information about nodes reachable from the graph
        roots to the given file.
        """
        print(file=file)
        print("%-15s %-25s %s" % ("Class", "Name", "File"), file=file)
        print("%-15s %-25s %s" % ("-----", "----", "----"), file=file)
        for m in sorted(self.iter_graph(), key=operator.attrgetter("identifier")):
            print(
                "%-15s %-25s %s" % (type(m).__name__, m.identifier, m.filename or ""),
                file=file,
            )

    #
    # Adding to the graph:
    #

    def add_script(self, script_path: os.PathLike) -> Script:
        """
        Add a script to the module graph and process imports

        Raises OSError when the script cannot be opened.
        """
        node = self.find_node(os.fspath(script_path))
        if node is not None:
            raise ValueError("adding {script_path!r} multiple times")

        node = self._load_script(script_path)
        self.add_root(node)
        self._run_stack()
        return node

    def add_module(self, module_name: str) -> BaseNode:
        """
        Add a module to the graph and process imports.

        Will not raise an exception for non-existing modules.
        """
        node = self.find_node(module_name)
        if node is None:
            node = self._find_or_load_module(None, module_name)

        self.add_root(node)
        self._run_stack()
        return node

    #
    # Hooks
    #

    def import_module(self, importing_module: BaseNode, import_name: str) -> BaseNode:
        """
        Import 'import_name' and add an edge from 'module' to 'import_name'

        This is an API to be used by hooks. The graph is not fully updated
        after calling this method.
        """
        node = self.find_node(import_name)
        if node is None:
            node = self._find_or_load_module(importing_module, import_name)
        self.add_edge(importing_module, node, DEFAULT_DEPENDENCY)
        return node

    def _run_post_processing(self, node: BaseNode) -> None:
        """
        Run the post processing hooks for the node.
        """
        self._delayed.finished(node)
        self._post_processing(self, node)

    def add_post_processing_hook(self, hook: ProcessingCallback) -> None:
        """
        Run 'hook(self, node)' when *node* is fully processed.
        """
        self._post_processing.add(hook)

    def add_missing_hook(self, hook: MissingCallback) -> None:
        """
        Run 'hook(self, module_name) -> node' before creating
        a MissingModule node.

        The result of the first registered hook that does
        not return None is used.
        """
        self._missing_hook.add(hook)

    def _create_missing_module(
        self, importing_module: Optional[BaseNode], module_name: str
    ):
        """
        Create a MissingModule node for 'module_name',
        after checking if one of the missing hooks can
        provide a node.
        """
        node = self._missing_hook(self, importing_module, module_name)
        if node is not None:
            return node

        node = MissingModule(module_name)
        self.add_node(node)
        self._process_import_list(node, ())
        return node

    def add_excludes(self, excluded_names: Iterator[str]) -> None:
        """
        Exclude the names in "excludeded_names" from the graph
        """
        if isinstance(excluded_names, str):
            raise TypeError(f"{excluded_names!r} is not a sequence of strings")

        for nm in excluded_names:
            self._global_lazy_nodes[nm] = None

    def add_implies(self, implies: Dict[str, ImpliesValueType]) -> None:
        """
        Add implied references for the graph.
        """
        for key, value in implies.items():
            # Implies are logically distinct from excludes and excludes have
            # precedence.
            if (
                key not in self._global_lazy_nodes
                or self._global_lazy_nodes[key] is not None
            ):
                self._global_lazy_nodes[key] = value

    #
    # Internal: building the graph
    #

    def _run_stack(self) -> None:
        """
        Process all items in the delayed work queue, until there
        is no more work.
        """
        while self._work_stack or self._delayed.have_finished_work():
            if self._delayed.have_finished_work():
                self._delayed.process_finished_nodes()

            if self._work_stack:
                func, args = self._work_stack.pop()
                func(*args)

        assert not self._delayed.has_unfinished, repr(self._delayed)

    def _implied_references(
        self, importing_module: Optional[BaseNode], module_name: str
    ) -> Optional[BaseNode]:
        """
        Process implied references and excludes for module_name
        """
        assert self.find_node(module_name) is None
        node: BaseNode

        if module_name in self._global_lazy_nodes:
            implied = self._global_lazy_nodes.pop(module_name)

            if implied is None:
                node = ExcludedModule(module_name)
                self.add_node(node)
                self._process_import_list(node, ())
                return node

            elif isinstance(implied, Alias):
                node = AliasNode(module_name, implied)
                assert self.find_node(module_name) is None

                self.add_node(node)
                self._process_import_list(node, ())

                other = self._find_or_load_module(node, implied)
                self.add_edge(node, other, DEFAULT_DEPENDENCY)
                return node

            else:
                node = self._find_or_load_module(importing_module, module_name)
                for ref in implied:
                    other = self._find_or_load_module(node, ref)
                    self.add_edge(node, other, DEFAULT_DEPENDENCY)

                return node

        else:
            return None

    def _load_module(
        self, importing_module: Optional[BaseNode], module_name: str
    ) -> BaseNode:
        """
        Add a node for a specific module.

        The module must not be part of the graph, and the
        module_name must be an absolute name (not a relative
        import.
        """
        node: BaseNode

        assert not module_name.startswith(".")
        assert self.find_node(module_name) is None

        try:
            try:
                spec = importlib.util.find_spec(module_name)

            except ValueError as exc:
                assert "__spec__" in exc.args[0]

                # See python issue #35791 and #35806. This is a
                # workaround for dealing with module-like objects
                # in sys.modules that cause problems with
                # importlib.util.find_spec.
                orig = sys.modules.pop(module_name)
                try:
                    spec = importlib.util.find_spec(module_name)
                finally:
                    assert module_name not in sys.modules
                    sys.modules[module_name] = orig

            if spec is None:
                node = self._create_missing_module(importing_module, module_name)
                return node

        except (ImportError, SyntaxError) as exc:
            if "." in module_name and (
                (
                    isinstance(exc, ModuleNotFoundError)
                    and ("No module named" in str(exc))
                )
                or isinstance(exc, SyntaxError)
            ):
                # find_spec actually imports parent packages, which can
                # cause problems when importing fails for some reason.
                #
                # Try to work around this by inserting a fake module object
                # in sys.modules and retrying.
                #
                # node_for_spec on a submodule is called only after
                # successfully calling node_for_spec on the parent package,
                # hence we know that find_spec will be successfull and
                # will find a pacakge with an __init__.py.
                parent = module_name.rpartition(".")[0]
                assert parent not in sys.modules

                spec = importlib.util.find_spec(parent)
                assert spec is not None

                path = spec.origin
                assert path is not None
                if path.endswith("__init__.py"):
                    path = os.path.dirname(path)
                sys.modules[parent] = cast(ModuleType, FakePackage([path]))
                return self._load_module(importing_module, module_name)

            else:
                node = self._create_missing_module(importing_module, module_name)
                return node

        node, imports = node_for_spec(spec, sys.path)

        if node.name != module_name:
            # Module is aliased in sys.modules. One example of
            # this is "os.path", which is a virtual submodule
            # that's an alias of one of the platforms specific
            # path modules (such as posixpath)

            alias_node = AliasNode(module_name, node.name)
            self.add_node(alias_node)
            self._process_import_list(alias_node, ())
            if self.find_node(node) is None:
                self.add_node(node)
                self._process_import_list(node, imports)

                containing_package, _ = split_package(node.name)
                if containing_package is not None:
                    # Ensure that the aliased node links back to its package
                    parent_node = self._find_or_load_module(None, containing_package)
                    self.add_edge(node, parent_node, DEFAULT_DEPENDENCY)

            self.add_edge(alias_node, node, DEFAULT_DEPENDENCY)
            return alias_node

        self.add_node(node)
        self._process_import_list(node, imports)

        return node

    def _load_script(self, script_path: os.PathLike) -> Script:
        """
        Load a given script.
        """
        assert self.find_node(os.fspath(script_path)) is None

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
        self, node: BaseNode, imports: Iterable[ImportInfo]
    ) -> None:
        """
        Schedule processing of all *imports* and the finalizer when
        that's done.
        """
        self._work_stack.append((self._run_post_processing, (node,)))

        for info in imports:
            self._work_stack.append((self._process_import, (node, info)))

    def _find_or_load_module(
        self,
        importing_module: Optional[BaseNode],
        module_name: str,
        *,
        link_missing_to_parent: bool = True,
    ) -> BaseNode:
        node: Optional[BaseNode] = None
        parent_node: Optional[BaseNode]

        node = self.find_node(module_name)
        if node is not None:
            return node

        containing_package, _ = split_package(module_name)
        if containing_package is not None:
            parent_node = self._find_or_load_module(
                importing_module, containing_package
            )
            if isinstance(parent_node, MissingModule):
                node = self._create_missing_module(importing_module, module_name)
            elif isinstance(parent_node, ExcludedModule):
                node = ExcludedModule(module_name)
                self.add_node(node)
                self._process_import_list(node, ())

        else:
            parent_node = None

        if node is None:
            node = self._implied_references(importing_module, module_name)
            if node is None:
                node = self._load_module(importing_module, module_name)

        assert node is not None

        if parent_node is not None and (
            link_missing_to_parent or not isinstance(node, MissingModule)
        ):
            self.add_edge(node, parent_node, DEFAULT_DEPENDENCY)

        return node

    def _process_import(
        self, importing_module: BaseNode, import_info: ImportInfo
    ) -> None:
        node: Optional[BaseNode]

        if import_info.import_level == 0:
            # Absolute import
            absolute_name = import_info.import_module

            node = self._find_or_load_module(importing_module, absolute_name)

            assert node is not None

            self.add_edge(
                importing_module, node, from_importinfo(import_info, False, None)
            )

            if import_info.import_names or import_info.star_import:
                self._delayed.wait_for(
                    importing_module,
                    node,
                    functools.partial(self._process_namelist, import_info=import_info),
                )

        else:
            # Relative import, calculate the absolute name
            importing_package = relative_package(
                importing_module, import_info.import_level
            )
            if importing_package is None:
                # Invalid relative import: points to outside of a top-level package
                invalid_name = (
                    "." * import_info.import_level
                ) + import_info.import_module
                node = self.find_node(invalid_name)
                if node is None:
                    node = InvalidRelativeImport(
                        ("." * import_info.import_level) + import_info.import_module
                    )
                    self.add_node(node)
                    self._process_import_list(node, ())

                else:
                    assert isinstance(node, InvalidRelativeImport)  # pragma: nocover

                self.add_edge(
                    importing_module, node, from_importinfo(import_info, False, None)
                )

                # Ignore the import_names and star_import attributes of import_info,
                # that would just add more InvalidRelativeImport nodes.
                return

            if import_info.import_module:
                absolute_name = f"{importing_package}.{import_info.import_module}"
            else:
                absolute_name = f"{importing_package}"

            assert absolute_name and absolute_name[0] != "."

            node = self._find_or_load_module(importing_module, absolute_name)

            assert node is not None

            self.add_edge(
                importing_module, node, from_importinfo(import_info, False, None)
            )

            self._delayed.wait_for(
                importing_module,
                node,
                functools.partial(self._process_namelist, import_info=import_info),
            )

        # See python issue #2506: The peephole optimizer confuses coverage.py
        # w.r.t. coverage of the previous statement unless the return statement
        # below is present.
        return

    def _process_namelist(
        self,
        importing_module: Union[Module, Package],
        imported_module: BaseNode,
        import_info: ImportInfo,
    ):
        assert isinstance(importing_module, (Module, Package))
        if import_info.star_import:
            if isinstance(imported_module, (Package, Module)):
                importing_module.globals_written.update(imported_module.globals_written)

        else:
            importing_module.globals_written.update(import_info.import_names)

            if import_info.import_names and isinstance(
                imported_module, (Package, NamespacePackage, AliasNode)
            ):
                if isinstance(imported_module, AliasNode):
                    node = self.find_node(imported_module.actual_module)
                    assert node is not None

                    imported_module = node
                    if not isinstance(imported_module, (Package, NamespacePackage)):
                        return

                for nm in import_info.import_names:
                    subnode = self._find_or_load_module(
                        importing_module,
                        f"{imported_module.identifier}.{nm}",
                        link_missing_to_parent=False,
                    )
                    if isinstance(subnode, MissingModule):
                        if nm in imported_module.globals_written:
                            # Name exists, but is not a module, don't add edge
                            # to the "missing" node

                            # Check if the imported name is actually some other imported
                            # module.
                            for ed_set, tgt in self.outgoing(imported_module):
                                # ed = cast(Optional[DependencyInfo], ed)
                                if (
                                    any(nm == ed.imported_as for ed in ed_set)
                                    or tgt.identifier == nm
                                ):
                                    self.add_edge(
                                        importing_module,
                                        tgt,
                                        from_importinfo(import_info, True, None),
                                    )
                                    break
                            continue

                        elif (
                            isinstance(imported_module, Package)
                            and imported_module.init_module.name == "@@SIX_MOVES@@"
                        ):
                            # six.moves is a virtual pseudo package that contains a
                            # number of names, some # aliases for modules, some alias
                            # for functions in other modules.
                            # #This block handles # the latter, while the former are
                            # handled by the graph builder.
                            if nm in SIX_MOVES_TO:
                                # function import
                                dep_node = self._find_or_load_module(
                                    importing_module, SIX_MOVES_TO[nm]
                                )
                                self.add_edge(
                                    importing_module, dep_node, DEFAULT_DEPENDENCY
                                )
                                continue

                    self.add_edge(subnode, imported_module, DEFAULT_DEPENDENCY)
                    self.add_edge(
                        importing_module,
                        subnode,
                        from_importinfo(import_info, True, None),
                    )
                    # else:
                    #    Node is not a package, therefore "from node import a" cannot
                    #    refer to a submodule.

        return
