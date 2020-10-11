"""
This module contains the definition of the ModuleGraph class.
"""
import ast
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
from ._depinfo import DependencyInfo, from_importinfo
from ._distributions import PyPIDistribution, distribution_named
from ._graphbuilder import SIX_MOVES_TO, node_for_spec, relative_package
from ._implies import STDLIB_IMPLIES, Alias, ImpliesValueType, Virtual
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
    VirtualNode,
)
from ._swig_support import swig_missing_hook
from ._utilities import FakePackage, split_package

ProcessingCallback = Callable[["ModuleGraph", BaseNode], None]
MissingCallback = Callable[["ModuleGraph", Optional[BaseNode], str], Optional[BaseNode]]

DEFAULT_DEPENDENCY = DependencyInfo(False, True, False, None)


class ModuleGraph(ObjectGraph[Union[BaseNode, PyPIDistribution], DependencyInfo]):
    """
    Class representing the dependency graph between a collection
    of python modules and scripts.

    The roots of the graph are those nodes that are added to the
    graph using :meth:`add_script() <ModuleGraph.add_script>` and
    :meth:`add_module() <ModuleGraph.add_module>`.

    Args:
      * use_stdlib_implies: Use the built-in implied actions for the stdlib.

      * use_builtin_hooks: Use the built-in extension hooks
    """

    _post_processing: CallbackList[ProcessingCallback]
    _missing_hook: FirstNotNone[MissingCallback]
    _work_stack: List[Tuple[Callable, tuple]]
    _global_lazy_nodes: Dict[str, ImpliesValueType]

    def __init__(
        self, *, use_stdlib_implies: bool = True, use_builtin_hooks: bool = True
    ):
        super().__init__()
        self._post_processing = CallbackList()
        self._missing_hook = FirstNotNone()
        self._work_stack = []

        self._global_lazy_nodes = {}

        # Reference to __main__ cannot be valid when multiple scripts
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

        This will not report PyPIDistributions that are nodes in the graph,
        unless they are also the *distribution* attribute of a node.

        Args:
          reacable: IF true only report on nodes that are reachable from
            a graph root, otherwise report on all nodes.
        """
        seen: Set[str] = set()
        for node in self.iter_graph() if reachable else self.nodes():
            if isinstance(node, PyPIDistribution):
                continue

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

        Args:
          file: Stream to write to
        """
        print(file=file)
        print("%-15s %-25s %s" % ("Class", "Name", "File"), file=file)
        print("%-15s %-25s %s" % ("-----", "----", "----"), file=file)
        for m in sorted(self.iter_graph(), key=operator.attrgetter("identifier")):
            if isinstance(m, PyPIDistribution):
                continue
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

        Args:
           script_path: Filesystem path for the script to be added

        Returns:
           The script node for the just added script

        Raises:
           ValueError: If the script is already part of the graph

           OSError: If the script cannot be opened.

           SyntaxError: If the script is invalid
        """
        node = self._find_module(os.fspath(script_path))
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

        Args:
           module_name: Name of the module to import.
        """
        node = self._find_module(module_name)
        if node is None:
            node = self._find_or_load_module(None, module_name)

        self.add_root(node)
        self._run_stack()
        return node

    def add_distribution(self, distribution: Union[PyPIDistribution, str]):
        """
        Add a package distribution to the graph, with references
        to all importable names in that distribution

        Args:
          distribution: A distribution or distribution name

        Returns
          The node added to the graph
        """
        if isinstance(distribution, str):
            tmp = distribution_named(distribution)
            if tmp is None:
                raise ValueError(f"Distribution {distribution} not found")

            distribution = tmp

        found = self.find_node(distribution.identifier)
        if found is not None:
            assert isinstance(found, PyPIDistribution)
            return found

        self.add_node(distribution)
        self.add_root(distribution)

        for module_name in distribution.import_names:
            node = self._find_or_load_module(None, module_name)
            self.add_edge(distribution, node, DEFAULT_DEPENDENCY)

        self._run_stack()
        return distribution

    #
    # Hooks
    #

    def import_module(self, importing_module: BaseNode, import_name: str) -> BaseNode:
        """
        Import 'import_name' and add an edge from 'module' to 'import_name'

        This is an API to be used by hooks. The graph is not fully updated
        after calling this method.

        Args:
          importing_module: The module that triggers this import

          import_name: The name that should be imported

        Returns
          The graph node for *import_name*.
        """
        node = self._find_module(import_name)
        if node is None:
            node = self._find_or_load_module(importing_module, import_name)

        self.add_edge(importing_module, node, DEFAULT_DEPENDENCY)
        return node

    def add_post_processing_hook(self, hook: ProcessingCallback) -> None:
        """
        Add a hook function to be ran whenever a node is fully processed.

        It is possible to add multip hooks by calling this method
        multiple times.

        Args:
           hook: The post processing hook.  Run ``hook(self, node)``
           when *node* is fully processed.
        """
        self._post_processing.add(hook)

    def add_missing_hook(self, hook: MissingCallback) -> None:
        """
        Add a hook function that's used to try to resolve a missing module.

        The hook functions are called in reverse order of addition,
        and the result of the first hook that doesn't return :data:`None`
        is used in the graph.

        Args:
          hook: The hook function. Run
             ``hook(self, importing_module, module_name)`` before
             creating a :class:`MissingModule` node for *module_name*.
        """
        self._missing_hook.add(hook)

    def _create_missing_module(
        self, importing_module: Optional[BaseNode], module_name: str
    ) -> BaseNode:
        """
        Create a MissingModule node for 'module_name',
        after checking if one of the missing hooks can
        provide a node.

        Args:
          imoprting_module: The node that triggered the import.

          module_name: The name that cannot be resolved.

        Returns:
          A new node, either the result of one of the hooks or
          a new :class:`MissingModule`.
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

        Excluded names can end up as :class:`ExcludedNode` nodes in the
        graph, but the dependencies of the actual module are not gathered.

        * excluded_names: An interator yielding names to exclude.
        """
        if isinstance(excluded_names, str):
            raise TypeError(f"{excluded_names!r} is not a sequence of strings")

        for nm in excluded_names:
            self._global_lazy_nodes[nm] = None

    def add_implies(self, implies: Dict[str, ImpliesValueType]) -> None:
        """
        Add implied actions for the graph.

        An implied action can be used for three purposes:
        * A list of dependencies.

          Commonly used to add module dependencies for modules
          that modulegraph2 cannot scan, such as extensions and modules
          using :func:`__import__`.

        * An :class:`Alias` for another node

          Used to mark an importable name as an alias for some
          other module. An example of this is :mod:`os.path`, which
          is an alias to a platform specific path module (such as
          :mod:`posixpath`.

        * A :class:`Virtual` module

          Used to mark an importable name as a virtual module
          that is added to :data:`sys.modules` by some other
          module.

        Args:
          implies: A mapping from module names to implied actions
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
        while self._work_stack:
            func, args = self._work_stack.pop()
            func(*args)

    def _implied_references(
        self, importing_module: Optional[BaseNode], module_name: str
    ) -> Optional[BaseNode]:
        """
        Check implied actions for *module_name*.

        Args:
         importing_module: Module triggering the import

         module_name: The name that should be imported

        Returns:
          A node if their are implied actions, or :data:`None`
          otherwise.
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

            elif isinstance(implied, Virtual):
                node = VirtualNode(module_name, implied)
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

        This not just adds the loaded module to the graph,
        but also pushed functions to the work stack that will
        process the import statements in *module_name*.

        Args:
          importing_module: The node triggering this import

          module_name: The name to be loaded

        Returns:
          A new node for *module_name*

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

            except AttributeError as exc:
                if "has no attribute '__path__'" in exc.args[0]:
                    # In Python 3.6 finding the spec dotted name
                    # that refers to an attribute of a module will
                    # result in an attribute error instead of returning
                    # None.
                    spec = None

                else:  # pragma: nocover
                    raise

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
                loader = spec.loader
                assert isinstance(loader, importlib.abc.InspectLoader)
                if loader.is_package(spec.name):
                    path = spec.origin
                    assert path is not None
                    assert path.rpartition(os.sep)[-1].startswith("__init__."), path
                    path = os.path.dirname(path)
                    sys.modules[parent] = cast(ModuleType, FakePackage([path]))
                    return self._load_module(importing_module, module_name)

                else:
                    node = self._create_missing_module(importing_module, module_name)
                    return node

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

        if isinstance(node, Package):
            # Hidden import in explicit namespace packages
            if node.namespace_type in {"pkgutil", "pkg_resources"}:
                nspkg = self._find_or_load_module(None, node.namespace_type)
                assert nspkg is not None
                self.add_edge(node, nspkg, DEFAULT_DEPENDENCY)

        self._process_import_list(node, imports)

        return node

    def _load_script(self, script_path: os.PathLike) -> Script:
        """
        Add a :class:`Script` node to the graph.

        The graph not contain  a script with *script_path*
        as its filesystem location. This also pushes work
        to the stack to process import statements in the
        script.


        Args:
          script_path: Filesystem path for a script

        Raises:
          OSError: If the script cannot be opened

          SyntaxError: If the script is invalid
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

        Args:
          node: The node for which the import list is processed

          imports: The imports to process
        """

        # Call postprocessing hooks when all imports are processed
        self._work_stack.append((self._post_processing, (self, node)))

        # Schedule work to process import statements.
        for info in imports:
            self._work_stack.append((self._process_import, (node, info)))

    def _find_module(self, module_name: Union[BaseNode, str]) -> Optional[BaseNode]:
        """
        Find a module in the graph. This is an alias for :meth:`find_node`
        that checks that the found node is actually a :class:`BaseNode`.

        Args:
          module_name: The name to look for

        Returns
          The node for *module_name*, or :data:`None` when there is
          no such node.

        Raises:
          AssertionError: When the node is found but of the wrong type.
            This should never happen as long as the *identifier* attributes
            of :class:`PyPIDistribution` and :class:`BaseNode` instances
            cannot overlap.
        """
        node = self.find_node(module_name)
        if node is not None:
            assert isinstance(node, BaseNode)
            return node

        return None

    def _find_or_load_module(
        self,
        importing_module: Optional[BaseNode],
        module_name: str,
        *,
        link_missing_to_parent: bool = True,
    ) -> BaseNode:
        """
        Locate the node for *module_name*, creating a new name if necessary.

        Args:
          importing_module: The node that triggers this import

          module_name: The name to load

          link_missing_to_parent: If true the function will link a
           :class:`MissingModule` node for *module_name* to
           *importing_module*.

        Returns:
          The node for *importing_module*.
        """
        node: Optional[BaseNode] = None
        parent_node: Optional[BaseNode]

        node = self._find_module(module_name)
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
        """
        Process a single import.

        This locates the node imported name (possibly pushing work to
        the stack to process its imports), and schedules a call to
        process the name list of the import statement when the
        imported name is fully processed.

        Args:
          importing_module: The node that this import pertains to.

          import_info: Information about an import
        """
        node: Optional[BaseNode]
        absolute_name: str

        if import_info.import_level == 0:
            # Absolute import
            absolute_name = str(import_info.import_module)

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
                node = self._find_module(invalid_name)
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

        #
        # Processing the name list for 'from ... import *namelist*` should
        # be done after importing the module we load the names from. This
        # means that function should be pushed on the work stack before
        # pushing any work needed to load the module.
        #
        # We need the node for the module while processing the namelist though,
        # therefore first resolve the module which may push some work on the
        # stack, then insert the call to _process_namelist just before all
        # work pushed by _find_or_load_module.
        #
        # This ensures that _process_namelist is called when all work pushed
        # by _find_or_load_module is done.
        #
        offset = len(self._work_stack)

        node = self._find_or_load_module(importing_module, absolute_name)

        assert node is not None

        self.add_edge(
            importing_module,
            node,
            from_importinfo(import_info, False, import_info.import_module.asname),
        )

        self._work_stack.insert(
            offset, (self._process_namelist, (importing_module, node, import_info))
        )

    def _process_namelist(
        self,
        importing_module: Union[Module, Package],
        imported_module: BaseNode,
        import_info: ImportInfo,
    ):
        """
        Process the name list for an import statement ('from ... import name_list').

        If *imported_module* is a package any imported names are assumed to
        be modules, unless there is clear evidence to the contrarary. For regular
        modules any imported names are assumed to refer to data (and won't
        result in :class:`MissingModule` nodes in the graph when names cannot
        be located).

        Args:
          importing_module: The module triggering the import

          imported_module: The imported module

          import_info: Information about the import
        """
        assert isinstance(importing_module, (Module, Package, Script))
        if import_info.star_import:
            if isinstance(imported_module, (Package, Module)):
                importing_module.globals_written.update(imported_module.globals_written)

        else:
            importing_module.globals_written.update(import_info.import_names)

            if import_info.import_names and isinstance(
                imported_module, (Package, NamespacePackage, AliasNode, Module)
            ):
                if isinstance(imported_module, AliasNode):
                    node = self._find_module(imported_module.actual_module)
                    assert node is not None

                    imported_module = node
                    if not isinstance(
                        imported_module, (Package, NamespacePackage, Module)
                    ):
                        return

                for nm in import_info.import_names:
                    if nm in imported_module.globals_written:
                        # Name exists as a global in the imported module,
                        # it is either a global or an imported module.
                        for ed_set, tgt in self.outgoing(imported_module):
                            if (
                                any(nm == ed.imported_as for ed in ed_set)
                                or tgt.identifier == nm
                            ):
                                self.add_edge(
                                    importing_module,
                                    tgt,
                                    from_importinfo(import_info, True, nm.asname),
                                )
                                break
                        continue

                    elif isinstance(imported_module, Module):
                        # Only packages can have importable names that are sub
                        # modules, therefore skip to the next name for "plain"
                        # modules.
                        continue

                    subnode = self._find_or_load_module(
                        importing_module,
                        f"{imported_module.identifier}.{nm}",
                        link_missing_to_parent=False,
                    )
                    if isinstance(subnode, MissingModule):
                        if (
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
                        from_importinfo(import_info, True, nm.asname),
                    )
        return
