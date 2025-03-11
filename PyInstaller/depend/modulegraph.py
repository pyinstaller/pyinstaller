#-----------------------------------------------------------------------------
# Copyright (c) 2005-2025, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
import dataclasses
import dis
import os
import sys
import typing
from collections import deque
from enum import Enum
from importlib import machinery as importlib_machinery, util as importlib_util
from importlib.machinery import ModuleSpec
from pathlib import Path

if typing.TYPE_CHECKING:
    from types import CodeType
    from typing import Optional, Deque, Tuple, Iterator, Union, Set, Dict, List, Any


class ModuleType(Enum):
    SPECIAL = None
    FROZEN = "FrozenModule"

    # A PURE module named __init__ (the root file of a package)
    PACKAGE = "Package"
    PURE = "SourceModule"
    NAMESPACE = "NamespacePackage"
    EXTENSION = "ExtensionModule"
    MISSING = "MissingModule"

    # A non-importable script (graph root node)
    SCRIPT = "Script"
    BUILTIN = "BuiltinModule"
    BYTECODE = "BytecodeModule"

    # Runtime modules and packages (dynamically defined at runtime)
    RUNTIME_MODULE = "RuntimeModule"
    RUNTIME_PACKAGE = "RuntimePackage"
    ALIAS = "Alias"


@dataclasses.dataclass
class Node:
    # This will either be a module name, or a script path
    ident: str
    # The type of module
    module_type: ModuleType
    # The path to the source file for this module, if it exists
    path: "Optional[os.PathLike]" = None
    # The importlib ModuleSpec for this module
    spec: "Optional[ModuleSpec]" = None
    # The code object for this module, if it's a Python module
    code: "Optional[CodeType]" = None
    # The target module if this is an Alias
    target: "Optional[str]" = None
    # The modules that import this node
    importing_modules: "Set[str]" = dataclasses.field(default_factory=set)
    # The modules this node imports
    dependencies: "Set[str]" = dataclasses.field(default_factory=set)

    def __eq__(self, other):
        if not isinstance(other, Node):
            return NotImplemented

        return self.ident == other.ident

    def __hash__(self):
        return hash(self.ident)

    def __repr__(self):
        return f"<Node {self.ident} ({self.module_type})>"


@dataclasses.dataclass(kw_only=True)
class QueueItem:
    # Fully qualified name for the module
    name: str
    path: "Optional[Path]" = None
    importing_module: "Optional[str]" = None
    import_level: int = 0
    is_script: bool = False
    fromlist: tuple[str] = tuple()


class ModuleGraph:
    """
    A representation of the dependencies of a Python module or script, represented
    as a directed graph.

    If you wish to understand how this graph functions, you should have a working
    knowledge of the basics of graph theory.

    This class is a modern reimplementation of the original ModuleGraph class from
    PyInstaller.lib.modulegraph.modulegraph. It uses Python's importlib machinery
    to find and analyze modules, and builds a graph of module dependencies.

    The graph is represented as a dictionary of nodes, where each node represents
    a module, and edges between nodes represent dependencies between modules.

    This implementation is designed to be more efficient and maintainable than the
    original, while maintaining compatibility with the rest of PyInstaller

    The new implementation:
    - Uses Python's importlib machinery for module resolution
    - Uses a queue-based approach for processing modules, rather than
      the recursive approach of the previous modulegraph
    - Handles circular imports gracefully
    - Scans bytecode for imports
    - Maintains compatibility with the original ModuleGraph API

    Usage:
    ```python
    graph = ModuleGraph()
    graph.add_script('path/to/script.py')
    # Access nodes and edges
    for node in graph.flatten():
        print(node.ident, node.module_type)
    ```
    """
    nodes: Dict[str, Node]
    excludes: Set[str]
    _queue: Deque[QueueItem]
    path: List[str]
    replace_paths: Tuple
    debug: int

    def __init__(
        self,
        path: Optional[List[str]] = None,
        excludes: Tuple[str] = (),
        replace_paths: Tuple = (),
        debug: int = 0
    ):
        """
        Initialize a new ModuleGraph instance.

        :param path: A list of directories to search for modules.
                     If not provided, sys.path is used.
        :param excludes: A list of module names to exclude from the graph.
        :param replace_paths: A list of (old, new) path tuples to replace paths in code objects.
        :param debug: Debug level (0-4). Higher values produce more output.
        """
        self.nodes = {"__main__": Node(ident="__main__", module_type=ModuleType.SPECIAL)}
        self.excludes = set(excludes)
        self._queue: "Deque[QueueItem]" = deque()
        self.path = path if path is not None else sys.path
        self.replace_paths = replace_paths
        self.debug = debug

    def msg(self, level: int, s: str, *args: Any) -> None:
        """
        Print a debug message with the given level.

        :param level: Debug level of the message.
        :param s: Message format string.
        :param args: Format string arguments.
        """
        if s and level <= self.debug:
            print(f"{s} {' '.join(map(repr(args)))}")

    def add_script(self, path: Union[str, Path]) -> Optional[Node]:
        """
        Create a node by path (not module name). It is expected to be a Python
        source file, and will be scanned for dependencies.

        :param path: Path to the Python script file.
        :return: The node created for the script.
        """
        if isinstance(path, str):
            path = Path(path)

        path = path.resolve()

        # Check if the script node already exists
        script_name = str(path)
        if script_name in self.nodes:
            return self.nodes[script_name]

        # Add to queue and process
        self._queue.append(QueueItem(name=script_name, path=path, is_script=True))
        self._run()

        # Return the created node
        return self.get_module(script_name)

    def add_module(self, module: str) -> Optional[Node]:
        """
        Add a module to the graph.

        :param module: The module to add, as a module name.
        :return: The node that was added, or None if the module was excluded.
        """

        # Otherwise, treat it as a module name
        if module in self.excludes:
            return None

        self._queue.append(QueueItem(name=module))
        self._run()

        return self.get_module(module)

    def add_exclude(self, module: str):
        """
        Exclude a module from the graph.

        :param module: Name of the module to exclude.
        """
        try:
            del self.nodes[module]
        finally:
            self.excludes.add(module)

    def alias_module(self, real_module_name: str, alias_module_name: str):
        """
        Alias the source module to the target module with the passed names.

        If the source module has not yet been added to the graph, then a graph node for the source module
        will be created as well as adding a reference from the target to the source module.

        :param real_module_name: Fully-qualified name of the **existing module** (i.e., the module being aliased).
        :param alias_module_name: Fully-qualified name of the **non-existent module** (i.e., the alias to be created).
        """

        if self.get_module(alias_module_name) is not None:
            raise ValueError(f"Module {alias_module_name} is already exists in the graph!")

        self.add_module(real_module_name)
        self._add_node(alias_module_name, ModuleType.ALIAS, target=real_module_name)

    def append_package_path(self, package_name: str, directory: Union[str, Path]) -> None:
        """
        Modulegraph does a good job at simulating Python's, but it cannot handle path modifications that packages
        make at runtime. This function provides a mechanism whereby you can register extra paths in this map for
        a package.

        :param package_name: Fully-qualified name of the package.
        :param directory: Absolute or relative path of the directory to be appended to this package's `__path__` attribute.
        """
        if not isinstance(directory, Path):
            directory: Path = Path(directory)

        # Get the package node
        package_node = self.get_module(package_name)
        if package_node is None or package_node.module_type not in (ModuleType.PACKAGE, ModuleType.NAMESPACE):
            # Not a package, can't append to its path
            return

        # Convert directory to absolute path if it's not already
        directory = directory.resolve()

        # Create a minimal spec if none exists
        if package_node.spec is None:
            package_node.spec = importlib_machinery.ModuleSpec(package_name, None)

        if not isinstance(package_node.spec.submodule_search_locations, list):
            package_node.spec.submodule_search_locations = []

        # Append the directory to the package's search locations if it's not already there
        if directory not in package_node.spec.submodule_search_locations:
            package_node.spec.submodule_search_locations.append(str(directory))

    def get_module(self, module: str) -> Optional[Node]:
        return self.nodes.get(module)

    def dependencies(self, node: Union[str, Node]) -> List[Node]:
        """
        Return a list of nodes that are referenced by the given node.

        :param node: The node to find outgoing references for.
        :return: List of nodes referenced by the given node.
        """
        if isinstance(node, str):
            maybe = self.get_module(node)
            if maybe is None:
                raise ValueError(f"Provided node does not exist in graph!")
            node = maybe

        return [self.nodes[ident] for ident in node.dependencies]

    def dependents(self, node: Union[str, Node]) -> List[Node]:
        """
        Return a list of nodes that reference the given node.

        :param node: The node to find incoming references for.
        :return: List of nodes that reference the given node.
        """
        if isinstance(node, Node):
            node = node.ident
        result = []
        for maybe in self.nodes.values():
            if node in maybe.dependencies:
                result.append(maybe)
        return result

    def flatten(self, start=None):
        """
        Iterate over all nodes in the graph in a breadth-first order.

        If start is specified, only nodes reachable from the start node are returned.

        :param start: The node to start traversal from. If None, all nodes are returned.
        :type start: str or Node or None
        :return: List of nodes in breadth-first order.
        :rtype: list
        """
        if start is None:
            # Return all nodes
            return list(self.nodes.values())

        # Start with the specified node
        if isinstance(start, str):
            start = self.nodes.get(start)
        if start is None:
            return []

        # Breadth-first traversal
        result = []
        visited = set()
        queue = deque([start])

        while queue:
            node = queue.popleft()
            if node.ident in visited:
                continue

            visited.add(node.ident)
            result.append(node)

            # Add outgoing nodes to the queue
            for outnode in self.dependencies(node):
                if outnode.ident not in visited:
                    queue.append(outnode)

        return result

    def get_code_using(self, module: str) -> "List[Tuple[str, CodeType]]":
        """
        Return a list of (modulename, code_object) for all modules in the graph
        that import the given module.

        :param module: Name of the module to find usages of.
        :return: List of (modulename, code_object) tuples for modules that import the given module.
        """
        module = self.get_module(module)
        if module is None:
            return []

        result = []
        for module_name in module.dependencies:
            maybe = self.get_module(module_name)
            if maybe is not None and maybe.code is not None:
                result.append((maybe.ident, maybe.code))

        return result

    def _add_node(
        self,
        ident: str,
        module_type: ModuleType,
        *,
        path: os.PathLike = None,
        spec: ModuleSpec = None,
        target: Optional[str] = None,
        code: Optional[CodeType] = None):
        """
        Add a node to the graph.

        :param ident: Identifier for the node (module name or script path).
        :param module_type: Type of the module.
        :param path: Path to the module file.
        :param spec: Module specification.
        :param target: Target for alias nodes
        :param code: The module's code object
        """
        if ident in self.excludes:
            return
        self.nodes[ident] = Node(ident, module_type, path=path, spec=spec, target=target, code=code)

    @staticmethod
    def _scan_code(code: "CodeType") -> "Iterator[Union[Tuple[str, int, Tuple[str]], Set[str]]]":
        """
        Scan a bytecode object for dependencies. Yields 3-tuples of
        `(name, level, fromlist)`.

        :param code: The code object to scan.
        :return: Iterator of tuples (name, level, fromlist) as each import is discovered,
                 followed by a set containing all the names that the code object provides.
        """

        objects = deque()
        objects.append((True, code))
        names = set()

        while objects:
            root, obj = objects.popleft()

            # We only ever require the most recent two names that were in a LOAD_CONST instruction
            loads = deque(maxlen=2)
            for inst in dis.get_instructions(obj):
                if inst.opcode == 100:  # LOAD_CONST
                    loads.append(inst.argval)
                elif inst.opcode == 108:  # IMPORT_NAME
                    # The import level, and the names imported.
                    # In the case of a star import, fromlist will be ('*',).
                    level, fromlist = loads
                    # The name of the module that was imported
                    name = inst.argval
                    yield name, level, fromlist
                elif root and inst.opcode in (90, 97):  # STORE_NAME, STORE_GLOBAL
                    names.add(inst.argval)
                elif root and inst.opcode in (91, 98):  # DELETE_NAME, DELETE_GLOBAL
                    names.remove(inst.argval)

            for const in obj.co_consts:
                if isinstance(const, CodeType):
                    # functions, classes etc. are not part of the main bytecode and instead are constants we need to
                    # separately analyze
                    objects.append((False, const))

        yield names

    def add_edge(self, from_name: str, to_name: str):
        """
        Add an edge between two nodes in the graph. This method will
        silently fail if either of the nodes does not exist.

        :param from_name: The name of the importing node.
        :param to_name: The name of the imported node.
        """
        to_node = self.get_module(to_name)
        from_node = self.get_module(from_name)

        if from_node is None or to_node is None:
            return

        to_node.importing_modules.add(from_name)
        from_node.dependencies.add(to_name)

    def _run(self):
        """
        Process the queue of modules to be imported.

        :return: None
        """

        while self._queue:
            item = self._queue.popleft()

            # Skip if the module has already been checked
            if self.get_module(item.name) is not None:
                # If we have an importing module, make sure to create the edge
                if item.importing_module and item.importing_module in self.nodes and item.name in self.nodes:
                    self.add_edge(item.importing_module, item.name)
                continue

            # Skip if the module is in the excludes list
            if item.name in self.excludes:
                continue

            module_spec = None
            try:
                module_spec = importlib_util.find_spec(item.name)
            except (ImportError, SyntaxError) as exc:
                if "." in item.name and (isinstance(exc, ModuleNotFoundError)
                                         and "No modul") or isinstance(exc, SyntaxError):
                    pass

            if item.is_script:
                # File path is provided for scripts
                module_path = item.path
            else:
                if module_spec is None:
                    # The module cannot be imported (see above) and therefore
                    # should be treated as a missing module
                    self._add_node(item.name, ModuleType.MISSING)
                    # Missing it may be, but if we have an importing module, create an edge
                    if item.importing_module and item.importing_module in self.nodes:
                        self.add_edge(item.importing_module, item.name)
                    continue
                # We have a path!
                module_path = module_spec.origin

            if module_path == "built-in":
                self._add_node(
                    item.name,
                    ModuleType.BUILTIN,
                    spec=module_spec,
                )
                # If we have an importing module, create an edge
                if item.importing_module and item.importing_module in self.nodes:
                    self.add_edge(item.importing_module, item.name)
            elif module_path == "frozen":
                self._add_node(item.name, ModuleType.FROZEN, spec=module_spec)
                # If we have an importing module, create an edge
                if item.importing_module and item.importing_module in self.nodes:
                    self.add_edge(item.importing_module, item.name)
            elif module_path is None:
                # Module path should only be None if it's a namespace package
                self._add_node(item.name, ModuleType.NAMESPACE, spec=module_spec)
                # If we have an importing module, create an edge
                if item.importing_module and item.importing_module in self.nodes:
                    self.add_edge(item.importing_module, item.name)

                if item.fromlist == ("*",):
                    # star imports from a namespace module are no-ops
                    continue

                # There's not much to do with namespace modules other than scan the things we're importing from them,
                # which could be modules.
                for name in item.fromlist:
                    self._queue.append(
                        QueueItem(
                            name=importlib_util.resolve_name(f".{name}", item.name),
                            importing_module=item.importing_module,
                        )
                    )
            else:
                module_path = Path(module_path).resolve()

                # Are we a source module? If so, analyse the bytecode
                if module_path.suffix in importlib_machinery.SOURCE_SUFFIXES:
                    module_type = ModuleType.SCRIPT if item.is_script else ModuleType.PURE
                    # __init__.py files require special handling in regard to submodule-resolution
                    # so they get their own module type
                    if not item.is_script and module_path.stem == "__init__":
                        module_type = ModuleType.PACKAGE
                    # TODO: consider using module_spec.cached to save compilation time?
                    code = compile(module_path.read_bytes(), str(module_path), "exec")

                # Bytecode files are already compiled, which saves us time, as we can just pull the code from the spec
                elif module_path.suffix in importlib_machinery.BYTECODE_SUFFIXES and isinstance(
                    module_spec.loader, importlib_machinery.SourcelessFileLoader
                ):
                    module_type = ModuleType.BYTECODE
                    code = module_spec.loader.get_code(item.name)

                # Extension modules. Make an entry and move on, we've got no way to analyse these.
                elif module_path.suffix in importlib_machinery.EXTENSION_SUFFIXES:
                    self._add_node(item.name, ModuleType.EXTENSION, path=module_path, spec=module_spec)
                    # If we have an importing module, create an edge
                    if item.importing_module and item.importing_module in self.nodes:
                        self.add_edge(item.importing_module, item.name)
                    continue
                else:
                    raise ValueError(f"Unknown file suffix for importable module: {module_path}")

                # Add the node before scanning the code to handle circular imports
                node = Node(ident=item.name, path=module_path, module_type=module_type, spec=module_spec, code=code)
                self.nodes[item.name] = node
                self._add_node(item.name, module_type, path=module_path, spec=module_spec, code=code)

                # If we have an importing module, create an edge
                if item.importing_module and item.importing_module in self.nodes:
                    self.add_edge(item.importing_module, item.name)

                imported_names = set()
                provided_names = set()

                for data in self._scan_code(code):
                    # _scan_code generates either (name, level, fromlist) or it returns a set
                    if not isinstance(data, set):
                        name, level, fromlist = data

                        # Resolve the name to an absolute name and add it to the queue
                        parent = getattr(
                            module_spec, "parent",
                            item.name.rpartition('.')[0] if '.' in item.name else None
                        )
                        try:
                            name = importlib_util.resolve_name(f"{'.' * level}{name}", parent)
                            self._queue.append(
                                QueueItem(name=name, fromlist=fromlist, importing_module=item.name, import_level=level)
                            )
                        except ImportError:
                            # Invalid relative import
                            self.msg(2, "Invalid relative import", name, level, parent)
                            continue
                    else:
                        provided_names = data

                # __init__.py files need a little special handling
                if module_type == ModuleType.PACKAGE:
                    if item.fromlist and item.fromlist != ("*",):
                        imported_names.update(item.fromlist)

                    # Add every name we import that the code doesn't directly provide
                    for name in imported_names - provided_names:
                        try:
                            submodule_name = importlib_util.resolve_name(f".{name}", item.name)
                            self._queue.append(QueueItem(
                                name=submodule_name,
                                importing_module=item.name,
                            ))
                        except ImportError:
                            # Invalid relative import
                            self.msg(2, "Invalid relative import", name, item.name)
                            continue
