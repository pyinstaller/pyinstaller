"""
The actual graph
"""
import sys
from typing import Optional, Tuple

from ._objectgraph import ObjectGraph


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
    #
    def __init__(self, *, path=None, debug=0):
        super().__init__(debug=debug)
        self._path = path if path is not None else sys.path
        self._post_processing = []

    #
    # Adding to the graph:
    #

    def add_script(self, script_path):
        # Create script node
        # Scan script for imports and add those to the queue
        ...

        self._roots.add(...)
        pass

    def add_module(self, module_name):
        self._roots.add(self._import_module(module_name))

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

    def _import_module(self, module_name, *, parent=None, edge_attributes=None):
        # XXX:
        # 1. Does module have reference to containing package (check modulegraph1)
        # 2. Does "import package.module" add reference to "package" as well as "package.module"
        #    -> Yes: both names are available in the importing module (ignoring "as")
        #
        # Locate module info
        # - Split module_name into parent package & module
        # - If parent is not None and not in graph:
        #   - Add something to the queue to resolve parent and then
        #     call this function again...
        # - Use importlib.find_spec to find module info
        # -

        # Create node
        # Scan module for imports and add those to the queue
        # Scan global code for assignments
        parent_package = None
        if parent is not None:
            parent_package, _ = split_package(parent)

        if module_name.startswith("."):
            if parent is None or parent_package is None:
                node = self.find_node(module_name)
                assert isinstance(node, InvalidImport)
                if node is None:
                    node = InvalidImport(module_name)
                    self._insert_node(node)
                    self._add_edge(self.find_node(parent), node, edge_attributes)

        package_name, base_name = split_package(module_name)
        package_node = None
        if package_name is not None:
            package_node = self.find_node(package_name)
            if package_node is None:
                package_node = self._import_module(
                    package_name, parent=parent, edge_attributes=edge_attributes
                )

            # XXX: only if _add_edge merges multiple edges!
            if parent is not None:
                self._add_edge(package_node, parent, edge_attributes=edge_attributes)

        # XXX: More complicated code is needed due to self.path...
        spec = importlib.util.find_spec(module_name, parent)
        if spec is None:
            # Not Found
            pass

        node = self.find_node(spec.name)
        if node is None:
            node = _node_for_spec(spec)

        self._insert_node(node)
        if parent is not None:
            self._add_edge(parent, node, edge_attributes)

        # XXX: Process node itself
        # XXX: Star imports can be problematic...
        # XXX: Can we recognize "from sys import path" as the harmless import of a global name (currently reported as MissingModule)?
