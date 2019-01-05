"""
The actual graph
"""
import os
import sys
from typing import Optional, Tuple, Union, TextIO

from ._objectgraph import ObjectGraph
from ._nodes import BaseNode, Script
from ._packages import PyPIDistribution


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


class ModuleGraph(ObjectGraph):
    # XXX: Split "ObjectGraph" functionality in base class.

    # Redesign of modulegraph.modulegraph.ModuleGraph
    # Gloal:
    # - minimal, but complete interface
    # - fully tested
    # - Python 3 only, use importlib and modern features
    #
    # Notes:
    # - This intentionally does not inherit from ObjectGraph,
    #   the dependency on altgraph will be removed once the
    #   basic functionality works
    #
    # XXX: Detect if "from mod import name" access a submodule
    #      or a global name.
    def __init__(self, *, path=None, debug=0):
        super().__init__(debug=debug)
        self._path = path if path is not None else sys.path
        self._post_processing = []
        self._work_q: Deque[Callable, tuple] = collections.deque()

        self.global_lazy_nodes: Dict[str, Optional[Alias]] ={ }
        self.distribution_lazy_nodes: Dict[str, Dict[str, Optional[Alias]]] = {}

    #
    # Reporting:
    #
    def report(self, stream: TextIO = sys.stdout):
        print(stream=stream)
        print("%-15s %-25s %s" % ("Class", "Name", "File"), stream=stream)
        print("%-15s %-25s %s" % ("-----", "----", "----"), stream=stream)
        for m in sorted(self.iter_graph(), key=lambda n: n.identifier):
            assert isinstance(m, BaseNode)
            print("%-15s %-25s %s" % (type(m).__name__, m.identifier, m.filename or ""), stream=stream)


    #
    # Adding to the graph:
    #

    def add_script(self, script_path: os.PathLike):
        """ Add a script to the module graph and process imports """
        self._roots.add(self._load_script(script_path))
        self._run_q()

    def add_module(self, module_name):
        self._roots.add(self._load_module(module_name))
        self._run_q()

    #
    # Hooks
    #

    def import_module(self, module, import_name):
        # Explicitly add edge to the graph, for use by hooks
        parent, _ = split_package(self.find_node(module).identifier)
        return self._import_module(module, parent=parent)

    def ignore_import(self, module, import_name):
        # XXX: Remove edge from "module" to "import_name" from the graph
        pass

    def _run_post_processing(self, node):
        for hook in self._post_processing:
            hook(self, node)

    def add_post_processing_hook(self, hook):
        """
        Run 'hook(self, node)' after *node* is fully processed.
        """
        self._post_processing.append(hook)

    #
    # Internal: building the graph
    #

    def _run_q(self):
        while self._work_q:
            func, args = self._work_q.popleft()
            func(args)

    def _load_implies_for_distribution(self, distribution: PyPIDistribution):
        """
        Load distribution specific implies into the global implies table
        """
        if distribution.name in self.distribution_lazy_nodes:
            lazy_nodes = self.distribution_lazy_nodes.pop(distribution.name)
            self.lazy_nodes.update(lazy_nodes)

    def _implied_references(self, full_name: str) -> Optional[BaseNode]:
        # XXX: This recurses...
        assert self._find_node(full_name) is None

        if node.identifier in self.lazy_nodes:
            implied = self.lazy_nodes.pop(node.identifier)

            if implied is None:
                node = ExcludedModule(full_name)
                self.add_node(node)
                return None

            elif isinstance(implied, Alias):
                node = AliasNode(full_name)
                other = self._load_module(implied)
                self.add_reference(node, other)
                return node

            else:
                node = self._load_module(module_name)
                for ref in implied:
                    other = self._load_module(ref)
                    self.add_reference(node, other)

                return node

        else:
            return None

    def _load_module(self, module_name: str) -> BaseNode:
        # module_name must be an absolute module name
        node = self._find_node(module_name)
        if node is not None:
            return None

        node = self._implied_references(full_name)
        if node is not None:
            return None

        spec = importlib.util.find_spec(module_name)

        node, imports = node_for_spec(module_name, spec)
        self.add_node(node)

        for info in imports:
            self._work_q.append((self.process_import, node, info))

        self._process_import_list(node, imports)
        return node

    def _process_imoprt_list(node, imports):
        if imports:
            self._work_q.append(self._run_post_processing, node)
        else:
            self._run_post_processing(node)

    def _load_script(self, script_path: os.PathLike) -> Script:
        node = Script(os.fspath(script_path)) # XXX
        self.add_node(node)

        with open(script_path, 'rb') as fp:
            source_bytes = fp.read()

        source_code = importlib.util.decode_source(source_bytes)
        ast_node = compile(source_code, os.fspath(script_path), "exec", flags=ast.PyCF_ONLY_AST, dont_inherit=True)
        imports = _ast_tools.extract_imports(ast_node)
        for info in imports:
            self._work_q.append((self.process_import, node, info))

        self._process_import_list(node, imports)
        return node

    def _process_import(self, importing_module: Optional[BaseNode], import_info: Union[_bytecode_tools.ImportInfo, _ast_tools.ImportInfo]):
        pass
