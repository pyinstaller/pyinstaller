#-----------------------------------------------------------------------------
# Copyright (c) 2005-2026, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
The module graph engine: discovery, resolution, and the dependency graph.

This module implements :class:`ModuleGraph`, the single class that powers
PyInstaller's dependency analysis. It answers the question "given this
script, what modules does the program *actually* need?" and records the
answer as a directed graph of :class:`~PyInstaller.depend.modulegraph.nodes.Node`
objects.

How an analysis works, step by step
-----------------------------------

1.  The caller adds a *root* to the graph: a script (``add_script``) or a
    module name (``import_hook`` / ``add_module``).
2.  Adding a root appends a :class:`~.nodes.QueueItem` to an internal
    ``collections.deque`` work queue. **Nothing recursive happens** -- the
    queue is what replaced the old modulegraph's recursive descent, which
    blew Python's recursion limit on deep import chains (upstream issues
    #2875, #2911, #3040, #3752; fixed by #2426 "make modulegraph
    non-recursive").
3.  ``_run()`` repeatedly pops one queue item and resolves it with
    ``_find_spec()``, which delegates to importlib's finders
    (``PathFinder``, ``FrozenImporter``, ``BuiltinImporter`` -- the same
    machinery a real ``import`` would use, per the importlib docs at
    https://docs.python.org/3/library/importlib.html).
4.  Pure-Python nodes get their file compiled once; the resulting code
    object is scanned for ``IMPORT_NAME`` instructions (``_scan_code``).
    Every import found is appended to the queue as a new ``QueueItem``, so
    the graph grows breadth-first until the queue drains.
5.  When the queue is empty, the graph holds one node per discovered module
    and edges connecting importers to the imported.

Extension points
----------------
``ModuleGraph`` subclasses
:class:`~PyInstaller.depend.modulegraph.hooks.ModuleGraphHooks`, which adds
PyInstaller's hook machinery (pre-safe-import-module, pre-find-module-path
and post-graph hooks, TOC generation, and friends). The engine itself only
*calls* a few well-defined extension-point methods; a plain ``ModuleGraph``
without hook caches behaves as a simple dependency tracer, which is what the
unit tests exercise.
"""

from __future__ import annotations

import dis
import os
import sys
import zipimport
from collections import deque
from copy import deepcopy
from importlib import machinery as importlib_machinery
from importlib import util as importlib_util
from importlib.machinery import BuiltinImporter, FrozenImporter, ModuleSpec, PathFinder
from pathlib import Path
from types import CodeType
from urllib.request import pathname2url

from PyInstaller import HOMEPATH
from PyInstaller import compat
from PyInstaller import log as logging
from PyInstaller.depend.modulegraph.hooks import ModuleGraphHooks
from PyInstaller.depend.modulegraph.implies import get_implies
from PyInstaller.depend.modulegraph.nodes import Alias, ModuleType, Node, QueueItem

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Dict, Iterator, List, Optional, Set, Tuple, Union, TextIO

    from PyInstaller.depend.imphook import ModuleHookCache


logger = logging.getLogger(__name__)


# HTML templates for the ModuleGraph cross-reference report (create_xref()).
header = """\
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8">
    <title>%(TITLE)s</title>
    <style>
      .node { padding: 0.5em 0 0.5em; border-top: thin grey dotted; }
      .moduletype { font: smaller italic }
      .node a { text-decoration: none; color: #006699; }
      .node a:visited { text-decoration: none; color: #2f0099; }
    </style>
  </head>
  <body>
    <h1>%(TITLE)s</h1>"""
entry = """
<div class="node">
  <a name="%(NAME)s"></a>
  %(CONTENT)s
</div>"""
contpl = """<tt>%(NAME)s</tt> <span class="moduletype">%(TYPE)s</span>"""
contpl_linked = """\
<a target="code" href="%(URL)s" type="text/plain"><tt>%(NAME)s</tt></a>
<span class="moduletype">%(TYPE)s</span>"""
imports = """\
  <div class="import">
%(HEAD)s:
  %(LINKS)s
  </div>
"""
footer = """
  </body>
</html>"""


class ModuleGraph(ModuleGraphHooks):
    """
    Directed graph of the modules a program depends on.

    Nodes are :class:`~.nodes.Node` instances keyed by their ``ident``
    (module name or script path) in :attr:`nodes`; edges are recorded on the
    nodes themselves (``Node.dependencies`` / ``Node.importing_modules``),
    so the whole graph lives in one dictionary.

    The class is intentionally *the* graph class -- there is no separate
    "PyiModuleGraph" wrapper any more. PyInstaller-specific behavior (hooks,
    TOC generation, ...) lives in the :class:`~.hooks.ModuleGraphHooks` base
    and is activated by passing ``pyi_homepath``; without it, the graph is a
    plain dependency tracer suitable for tests and tools.
    """

    def __init__(
        self,
        path: Optional[List[str]] = None,
        excludes: Tuple[str, ...] = (),
        implies: Optional[Dict[str, Union[List[str], Alias, None]]] = None,
        debug: int = 0,
        pyi_homepath: Optional[str] = None,
        user_hook_dirs: Tuple[Tuple[str, int], ...] = (),
    ):
        """
        Create an empty module graph.

        :param path: Search path (a list of directories) used to resolve
            top-level module names. Defaults to ``sys.path``. PyInstaller
            prepends the spec file's ``pathex`` entries to this after
            construction.
        :param excludes: Names of modules that must never enter the graph.
            Imports of excluded modules are dropped silently.
        :param implies: Mapping of module name -> dependencies the module
            pulls in from C code or otherwise untrackable places (see
            :mod:`PyInstaller.depend.modulegraph.implies`). Values may be a
            list of module names, an :class:`~.nodes.Alias`, or ``None`` to
            record the node while skipping its (untrackable) imports.
        :param debug: Verbosity for the graph's own debug messages (0-4).
        :param pyi_homepath: PyInstaller's home directory. When given (and
            only then), the PyInstaller hook machinery is set up and the
            ``base_library.zip`` modules are analyzed. Leave ``None`` for a
            standalone graph.
        :param user_hook_dirs: Extra hook directories as ``(path, priority)``
            tuples; only meaningful together with ``pyi_homepath``.
        """
        # The graph itself: node name -> Node. Seeded with a SPECIAL
        # placeholder so there is always a root object to attach the first
        # script to.
        self.nodes: Dict[str, Node] = {
            "__main__": Node(ident="__main__", module_type=ModuleType.SPECIAL)
        }

        # Names that must never enter the graph. Excluded imports are dropped
        # when they are encountered, not when they are queued, so that a
        # module excluded *after* being queued is still skipped.
        self.excludes: Set[str] = set(excludes)

        # The work queue driving the whole analysis. See the class docstring.
        self._queue: "deque[QueueItem]" = deque()

        # Module search path. Copy sys.path rather than aliasing it: PyInstaller
        # mutates this list per build (spec ``pathex``), and sys.path must not
        # be affected.
        self.path: List[str] = list(path) if path is not None else list(sys.path)

        # Implied dependencies (see ``implies`` parameter documentation).
        self._implies: Dict[str, Union[List[str], Alias, None]] = dict(implies) if implies else {}

        # Debug verbosity for self.msg() calls issued by the engine itself.
        self.debug = debug

        # -- PyInstaller-specific state (populated by _setup_hooks when
        #    pyi_homepath is given; left None for standalone graphs) --
        # The node of the first script added; the root all TOCs are built
        # from. Scripts added later are attached below it so the graph stays
        # a single connected tree.
        self._top_script_node: Optional[Node] = None
        # Base modules that every program depends on (populated by
        # _analyze_base_modules when pyi_homepath is given; empty for
        # standalone graphs that only track explicit imports).
        self._base_modules: List[Node] = []
        # Hook caches; see ModuleGraphHooks._setup_hooks() for details.
        self._hooks: Optional["ModuleHookCache"] = None
        self._hooks_pre_safe_import_module: Optional["ModuleHookCache"] = None
        self._hooks_pre_find_module_path: Optional["ModuleHookCache"] = None
        # Legacy (setuptools-style) namespace packages discovered from
        # installed distribution metadata; see scan_legacy_namespace_packages().
        self._legacy_ns_packages: Dict[str, List[str]] = {}

        if pyi_homepath is not None:
            # Full PyInstaller setup: hook caches, run-time hook registry and
            # the base_library.zip module analysis.
            self._homepath = pyi_homepath
            self._setup_hooks(user_hook_dirs)
            self._analyze_base_modules()

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------
    # msg()/msgin()/msgout() are provided by ModuleGraphHooks; they route the
    # engine's debug chatter through PyInstaller's logging system so that it
    # appears interleaved with the rest of the build log.

    # ------------------------------------------------------------------
    # Adding roots and modules
    # ------------------------------------------------------------------

    def _add_script_base(self, path: Union[str, Path]) -> Optional[Node]:
        """
        Add a script (the program's entry point) to the graph.

        The script is identified by *path*, not by module name -- scripts are
        not importable. Its file is compiled and scanned for imports like any
        other pure-Python node; the node type is
        :attr:`ModuleType.SCRIPT`.

        NOTE: this is the low-level engine implementation. The public
        ``add_script`` is provided by the ``ModuleGraphHooks`` mixin, which
        wraps this method to add PyInstaller-specific behavior (top-level
        script bookkeeping, friendly syntax-error reporting). Defining
        ``add_script`` here as well would shadow the mixin's version due to
        Python's MRO and silently drop that behavior.

        :param path: Path to the script file. Relative paths are resolved
            against the current working directory.
        :return: The node created for the script, or the existing node if
            this exact path was analyzed before.
        :raises FileNotFoundError: If the script does not exist.
        """
        path = Path(path).resolve()

        # Fail early (and clearly) for nonexistent scripts; the old graph
        # surfaced this as a confusing mid-analysis ImportError.
        if not path.is_file():
            raise FileNotFoundError(f"Script {str(path)!r} does not exist")

        # Scripts are keyed by their resolved path string, which is also what
        # TOC generation expects (Script nodes carry the full path).
        script_name = str(path)
        if script_name in self.nodes:
            return self.nodes[script_name]

        self._queue.append(QueueItem(name=script_name, path=str(path), is_script=True))
        self._run()

        return self.nodes.get(script_name)

    def add_module(self, module: str) -> Optional[Node]:
        """
        Add a module to the graph by fully-qualified name and analyze it.

        Unlike :meth:`import_hook`, this never raises for unresolvable
        modules -- they simply become :attr:`ModuleType.MISSING` nodes. Use
        this for modules whose absence is not an error (runtime hooks, hook
        machinery, ...).

        :param module: Fully-qualified name of the module.
        :return: The node for the module, or ``None`` if it is excluded.
        """
        if module in self.excludes:
            return None

        self._queue.append(QueueItem(name=module))
        self._run()

        return self.nodes.get(module)

    def import_hook(self, module: str, caller: "Union[str, Node, None]" = None) -> List[Node]:
        """
        Add a module to the graph, treating failure as an error.

        This mirrors the old modulegraph ``import_hook()`` contract, which
        :meth:`add_hiddenimports` and the hook machinery rely on: hidden
        imports that cannot be resolved must surface as ``ImportError`` so
        the caller can warn instead of failing the whole build silently.

        :param module: Fully-qualified name of the module.
        :param caller: Optional node (or node name) the import is attributed
            to; an edge is drawn from it to the new module.
        :return: Single-element list containing the module's node.
        :raises ImportError: If the module cannot be resolved (or is excluded).
        """
        node = self.find_node(module)
        if node is None:
            self._queue.append(QueueItem(name=module, importing_module=_ident_of(caller)))
            self._run()
            node = self.nodes.get(module)
            if node is None or node.module_type == ModuleType.MISSING:
                raise ModuleNotFoundError(f"No module named {module!r}")

        if caller is not None:
            self.add_edge(caller, node)
        return [node]

    def add_runtime_module(self, module_name: str) -> Optional[Node]:
        """
        Register a module that exists only at run time.

        Runtime modules (``six.moves`` and friends) are created by executing
        code, so there is no file to find. Hooks declare them via
        ``pre_safe_import_module()`` hooks (through
        ``PreSafeImportModuleAPI.add_runtime_module()``) so subsequent
        ``from runtime_module import x`` imports resolve in the graph.

        The node is created immediately (no resolution pass) and its
        ``from``-style attribute imports are left for post-graph hooks to
        handle.
        """
        node = Node(ident=module_name, module_type=ModuleType.RUNTIME_MODULE)
        self.nodes[module_name] = node
        return node

    def add_runtime_package(self, package_name: str) -> Optional[Node]:
        """
        Register a *package* that exists only at run time.

        Same as :meth:`add_runtime_module`, but the node is marked as a
        package so that ``from runtime_package import submodule`` imports are
        resolved against it.
        """
        node = Node(ident=package_name, module_type=ModuleType.RUNTIME_PACKAGE)
        self.nodes[package_name] = node
        return node

    def alias_module(self, real_module_name: str, alias_module_name: str):
        """
        Make ``alias_module_name`` behave like ``real_module_name``.

        The alias is registered in the implies registry; the next time a
        queue item for the alias name is processed, an :attr:`ModuleType.ALIAS`
        node is created for it and the real module is analyzed in its place.
        This mirrors the old modulegraph ``lazynodes`` behavior, where the
        mapping was recorded lazily and consulted by ``findNode()``.

        Nothing is resolved eagerly here: resolving (``add_module()``) would
        run the work queue, which may process queue items for *other* alias
        names whose implies entries have not been registered yet -- hooks
        typically register a whole set of aliases in a loop -- turning them
        into real nodes instead of aliases (e.g. the real ``wheel`` package
        shadowing ``setuptools._vendor.wheel``).

        :param real_module_name: Fully-qualified name of the existing module.
        :param alias_module_name: Fully-qualified name of the alias to create.
        """
        # If the alias name already exists in the graph, it is an error unless
        # it is an alias node pointing at the very same real module (i.e. the
        # alias is being re-registered idempotently, e.g. by hooks that run
        # more than once).
        existing = self.find_node(alias_module_name)
        if existing is not None and not (
            existing.module_type == ModuleType.ALIAS and existing.target == real_module_name
        ):
            raise ValueError(f"Module {alias_module_name!r} already exists in the graph!")

        # (Re-)register the implies entry: the node-side machinery creates
        # the ALIAS node (and analyzes the real module) when the alias name
        # is next processed. Re-registering is harmless, and needed after a
        # re-registration because the entry is popped once consumed.
        self._implies[alias_module_name] = Alias(real_module_name)

    def append_package_path(self, package_name: str, directory: Union[str, Path]) -> None:
        """
        Append a directory to a package's module search locations.

        Python packages can modify their ``__path__`` at run time (e.g. via
        ``pkgutil.extend_path``); static analysis cannot see that. This
        method lets hooks and spec files register the extra directories so
        submodule resolution inside the graph honors them.

        :param package_name: Fully-qualified name of the package.
        :param directory: Directory to append to the package's search
            locations.
        """
        package_node = self.find_node(package_name)
        if package_node is None:
            return

        # Only packages (regular or namespace) have search locations to
        # extend; appending to anything else would be meaningless.
        if package_node.module_type not in (ModuleType.PACKAGE, ModuleType.NAMESPACE):
            return

        # The node's spec carries the search locations. Fabricate a minimal
        # spec if the package was created without one (e.g. a runtime
        # package); importlib's ModuleSpec constructor is documented at
        # https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec
        if package_node.spec is None:
            package_node.spec = importlib_machinery.ModuleSpec(package_name, None, is_package=True)

        if not isinstance(package_node.spec.submodule_search_locations, list):
            package_node.spec.submodule_search_locations = []

        directory = str(Path(directory).resolve())
        if directory not in package_node.spec.submodule_search_locations:
            package_node.spec.submodule_search_locations.append(directory)

    def add_exclude(self, module: str) -> None:
        """
        Exclude a module from the graph, now and for all future imports.

        If the module is already in the graph its node is removed, but edges
        pointing at it are left dangling on purpose: importers keep their
        record that they imported the (now excluded) module, which keeps the
        build warnings accurate.

        :param module: Fully-qualified name of the module to exclude.
        """
        # pop(None) rather than ``del``: excluding a module that is not in
        # the graph (yet) must not raise.
        self.nodes.pop(module, None)
        self.excludes.add(module)

    # ------------------------------------------------------------------
    # Lookup and traversal
    # ------------------------------------------------------------------

    def find_node(self, name: str) -> Optional[Node]:
        """
        Return the node with the given name, or ``None`` if it is not in the
        graph. This is the canonical lookup method (issue #5812 maps the old
        ``findNode()`` here).
        """
        return self.nodes.get(name)

    def dependencies(self, node: "Union[str, Node]") -> List[Node]:
        """
        Return the nodes this node imports ("outgoing" edges).
        """
        node = self._resolve_arg(node)
        return [self.nodes[ident] for ident in node.dependencies if ident in self.nodes]

    def dependents(self, node: "Union[str, Node]") -> List[Node]:
        """
        Return the nodes that import this node ("incoming" edges).

        Edges are stored on the *importing* node, so finding importers is a
        scan over all nodes. That is fine: the scan is O(n) with tiny
        constants, and it happens a handful of times per build.
        """
        name = _ident_of(node)
        return [other for other in self.nodes.values() if name in other.dependencies]

    def outgoing(self, node: "Union[str, Node]") -> "Iterator[Tuple[None, Node]]":
        """
        Yield ``(edge_data, node)`` for every module this node imports.

        The edge-data element exists to match the ``modulegraph2``-style API
        agreed on in issue #5812 (``getReferences()`` -> ``outgoing()``).
        This engine does not track per-edge attributes, so it is always
        ``None``.
        """
        for imported in self.dependencies(node):
            yield None, imported

    def incoming(self, node: "Union[str, Node]") -> "Iterator[Tuple[None, Node]]":
        """
        Yield ``(edge_data, node)`` for every module importing this node.

        See :meth:`outgoing` for why the edge-data element is always
        ``None``.
        """
        for importer in self.dependents(node):
            yield None, importer

    def iter_graph(self, start: "Union[str, Node, None]" = None) -> List[Node]:
        """
        Return the graph's nodes in breadth-first order.

        With ``start`` given, only nodes reachable from it are returned --
        which is what every TOC-building call site wants, since the top-level
        script is the root of everything the program needs. Without ``start``
        (or for a standalone graph), all nodes are returned.

        This is the API renamed from the old modulegraph's ``flatten()``
        (issue #5812: ``flatten`` -> ``iter_graph``).
        """
        if start is None:
            return list(self.nodes.values())

        start = self._resolve_arg(start)

        # Standard breadth-first traversal over the outgoing edges.
        result: List[Node] = []
        visited: Set[str] = set()
        queue: "deque[Node]" = deque([start])
        while queue:
            node = queue.popleft()
            if node.ident in visited:
                continue
            visited.add(node.ident)
            result.append(node)
            for imported in self.dependencies(node):
                if imported.ident not in visited:
                    queue.append(imported)
        return result

    # ------------------------------------------------------------------
    # Edges
    # ------------------------------------------------------------------

    def add_edge(self, from_name: "Union[str, Node]", to_name: "Union[str, Node]") -> None:
        """
        Record that ``from_name`` imports ``to_name``.

        Both arguments may be node names or node objects. Edges to nodes
        that are not (yet) in the graph are dropped silently -- the caller
        usually means to reference a module that will be queued separately,
        and a dangling edge would resurrect a node the analysis excluded.

        The edge is recorded on both endpoints (``dependencies`` of the
        importer, ``importing_modules`` of the imported), so either direction
        can be walked in O(1).
        """
        from_node = self._resolve_arg(from_name, required=False)
        to_node = self._resolve_arg(to_name, required=False)
        if from_node is None or to_node is None:
            return

        to_node.importing_modules.add(from_node.ident)
        from_node.dependencies.add(to_node.ident)

    def remove_reference(self, from_name: "Union[str, Node]", to_name: "Union[str, Node]") -> None:
        """
        Remove the edge ``from_name`` -> ``to_name``.

        If the imported node loses its last importer it becomes unreachable,
        and it is deleted from the graph entirely (matching the old
        ``removeReference()`` behavior that hooks rely on via
        ``PostGraphAPI.del_imports()``).
        """
        from_node = self._resolve_arg(from_name, required=False)
        to_name = _ident_of(to_name)

        if from_node is None:
            return
        if to_name in from_node.dependencies:
            from_node.dependencies.remove(to_name)

        to_node = self.nodes.get(to_name)
        if to_node is None:
            return
        if from_node.ident in to_node.importing_modules:
            to_node.importing_modules.remove(from_node.ident)

        # The node is now unreachable from any root: nothing imports it (and
        # its own imports die with it), so it can never be frozen. Remove it
        # so later graph walks and TOCs do not resurrect it.
        if not to_node.importing_modules:
            del self.nodes[to_name]

    def remove_all_edges(self, node: "Union[str, Node]") -> None:
        """
        Detach a node from the graph by removing every edge to and from it.

        Implements the last outstanding ``modulegraph2`` API rename from
        issue #5812 (``removeReference()`` -> ``remove_all_edges()``).
        """
        node = self._resolve_arg(node)

        # Remove the node from all of its importers' dependency sets.
        for importer_name in list(node.importing_modules):
            importer = self.nodes.get(importer_name)
            if importer is not None:
                importer.dependencies.discard(node.ident)
        node.importing_modules.clear()

        # Tell everything this node imported that the edge is gone.
        for imported_name in list(node.dependencies):
            imported = self.nodes.get(imported_name)
            if imported is not None:
                imported.importing_modules.discard(node.ident)
        node.dependencies.clear()

    # ------------------------------------------------------------------
    # Namespace packages (legacy, setuptools-style)
    # ------------------------------------------------------------------

    def scan_legacy_namespace_packages(self) -> None:
        """
        Discover legacy (setuptools-style) namespace packages.

        Legacy namespace packages span several installed distributions whose
        ``__init__.py`` calls ``pkgutil.extend_path()``. Static analysis
        cannot run that call, so the mapping of package name -> extra search
        directories is recovered from the distributions' own metadata
        (``namespace_packages.txt``) and later merged into the package's
        search locations by :meth:`_find_spec`.

        This is the groundwork for upstream issue #4425 ("pkgutil-style
        namespace packages don't work"): without this scan, only the
        distribution that happens to be found first contributes submodules.
        """
        from collections import defaultdict

        legacy_ns_packages: Dict[str, Set[str]] = defaultdict(set)

        for dist in compat.importlib_metadata.distributions():
            ns_packages = dist.read_text("namespace_packages.txt")
            if ns_packages is None:
                continue
            # Obtain path to dist metadata directory. Might be a
            # zipfile.Path if the distribution is a zipped egg.
            dist_path = getattr(dist, '_path', None)
            if dist_path is None:
                continue
            for package_name in ns_packages.splitlines():
                path = os.path.join(str(dist_path.parent), *package_name.split('.'))
                legacy_ns_packages[package_name].add(path)

        self._legacy_ns_packages = {
            package_name: list(paths) for package_name, paths in legacy_ns_packages.items()
        }

    # ------------------------------------------------------------------
    # Module resolution
    # ------------------------------------------------------------------

    def _find_spec(self, fullname: str, search_dirs: Optional[List[str]] = None) -> Optional[ModuleSpec]:
        """
        Resolve ``fullname`` to an importlib ModuleSpec without importing it.

        Resolution order (documented per the importlib reference,
        https://docs.python.org/3/library/importlib.html):

        1.  If a ``pre_find_module_path`` hook supplied explicit
            ``search_dirs``, search exactly those.
        2.  For dotted names whose parent package is already a graph node,
            search the parent's ``submodule_search_locations`` -- this honors
            both regular packages and ``append_package_path()`` extensions.
        3.  For top-level names, search the graph's own ``path`` (which
            includes the spec file's ``pathex``), then fall back to the
            frozen and builtin importers -- ``PathFinder`` never finds those,
            but ``import sys`` must still resolve.
        4.  As a last resort for dotted names whose parent is not in the
            graph, use ``importlib.util.find_spec()``. Note that per the
            docs this *imports the parent package*; it is a documented,
            accepted side effect for this rare fallback path.
        5.  Legacy namespace package locations from installed distribution
            metadata are merged in, fixing up packages whose ``__path__``
            spans multiple distributions (issue #4425).

        :return: The ModuleSpec, or ``None`` if the module cannot be found.
        """
        # -- 0: a pre-find-module-path hook may override the search dirs. --
        # Hooks run at most once per module (the cache entry is popped).
        if search_dirs is None and self._hooks_pre_find_module_path is not None:
            hook = self._hooks_pre_find_module_path.pop(fullname, None)
            if hook is not None:
                search_dirs = self._run_pre_find_module_path_hook(hook, fullname)

        # -- 1: explicit search dirs (from the hook above, or a caller). --
        if search_dirs is not None:
            try:
                return PathFinder.find_spec(fullname, search_dirs)
            except ModuleNotFoundError:
                # See _make_namespace_spec(): namespace submodules whose
                # parent is not imported cannot be resolved by PathFinder.
                return self._make_namespace_spec(fullname, search_dirs)

        # -- 5 (early): merge legacy namespace package locations. --
        # Applied to whatever spec we end up with below.
        spec = self._find_spec_via_finders(fullname)

        legacy_paths = self._legacy_ns_packages.get(fullname)
        if legacy_paths:
            if spec is None:
                # The package was not found on disk at all, but a
                # distribution claims to provide part of it: fabricate a
                # namespace-style spec.
                spec = importlib_machinery.ModuleSpec(fullname, None, is_package=True)
                spec.submodule_search_locations = list(legacy_paths)
            elif spec.submodule_search_locations is not None:
                # Regular or namespace package: extend its search locations.
                for legacy_path in legacy_paths:
                    if legacy_path not in spec.submodule_search_locations:
                        spec.submodule_search_locations.append(legacy_path)

        return spec

    def _make_namespace_spec(self, fullname: str, search_dirs: List[str]) -> Optional[ModuleSpec]:
        """
        Emulate a PEP 420 namespace-package lookup for a submodule whose
        parent package is not imported.

        ``PathFinder.find_spec()`` cannot build namespace specs for dotted
        names: the ``_NamespacePath`` machinery it uses hard-requires the
        parent module to be present in ``sys.modules``
        (``_NamespacePath._get_parent_path()`` raises ``ModuleNotFoundError``
        otherwise). This graph resolves modules *without* importing them, so
        a directory without ``__init__.py`` nested inside an unimported
        package is invisible to the standard machinery.

        This method replicates what ``PathFinder`` would do: scan
        *search_dirs* for a directory named after the module's tail, and
        fabricate a loader-less spec with a **plain list** of the matching
        directories as search locations (never a lazy ``_NamespacePath``,
        which would raise again on later use).

        :param fullname: Fully-qualified (dotted) module name.
        :param search_dirs: Directories to scan for the module directory.
        :return: The fabricated :class:`ModuleSpec`, or ``None`` if no
            matching directory exists in *search_dirs*.
        """
        tail = fullname.rpartition('.')[2]
        portions = []
        for directory in search_dirs:
            candidate = Path(directory) / tail
            if candidate.is_dir():
                portions.append(str(candidate))
        if not portions:
            return None
        spec = importlib_machinery.ModuleSpec(fullname, None, is_package=True)
        spec.submodule_search_locations = portions
        return spec

    def _resolve_submodule_chain(self, fullname: str) -> Optional[ModuleSpec]:
        """
        Resolve a dotted module name whose *direct parent* is unknown, by
        walking up to the deepest ancestor present in the graph and then
        resolving each remaining component inside the ancestor's search
        locations.

        Importing ``package.subpackage.sub`` requires only that ``package``
        be locatable -- ``package.subpackage`` itself never needs to be
        (and often is not) in the graph. The standard machinery handles
        this by importing parents one by one; since this graph resolves
        without importing, the chain is walked *through the graph* instead:

        1. Find the longest dotted prefix of *fullname* whose node exists
           and has ``submodule_search_locations`` (i.e. is a package).
        2. For each remaining component, resolve it within the current
           locations with ``PathFinder.find_spec()``; directories without
           an ``__init__`` (namespace portions) fall back to
           :meth:`_make_namespace_spec`.
        3. Each resolved package component's search locations become the
           search path for the next component.

        :param fullname: Fully-qualified (dotted) module name.
        :return: The final :class:`ModuleSpec`, or ``None`` if no ancestor
            is in the graph or any component cannot be resolved.
        """
        parts = fullname.split(".")

        # 1: longest known package ancestor.
        anchor_len = 0
        locations: Optional[List[str]] = None
        for i in range(len(parts) - 1, 0, -1):
            prefix = ".".join(parts[:i])
            ancestor = self.find_node(prefix)
            if ancestor is not None and ancestor.spec is not None:
                ancestor_locations = ancestor.spec.submodule_search_locations
                if ancestor_locations:
                    anchor_len = i
                    locations = list(ancestor_locations)
                    break
        if locations is None:
            return None

        # 2: resolve each remaining component within the current locations.
        current = ".".join(parts[:anchor_len])
        spec: Optional[ModuleSpec] = None
        for part in parts[anchor_len:]:
            current = f"{current}.{part}"
            try:
                spec = PathFinder.find_spec(current, locations)
            except ModuleNotFoundError:
                # See _make_namespace_spec(): parent not imported.
                spec = self._make_namespace_spec(current, locations)
            if spec is None:
                return None
            if spec.submodule_search_locations:
                locations = list(spec.submodule_search_locations)
            elif current != fullname:
                # A non-package module in the middle of the chain: nothing
                # can live below it.
                return None
        return spec

    def _find_spec_via_finders(self, fullname: str) -> Optional[ModuleSpec]:
        """
        The finder chain of :meth:`_find_spec`, without the hook and
        legacy-namespace fix-ups. See :meth:`_find_spec` for the rationale
        of each step.
        """
        if "." in fullname:
            # Submodule: search the parent package's locations if known.
            parent_name = fullname.rpartition('.')[0]
            parent_node = self.find_node(parent_name)
            if parent_node is not None and parent_node.spec is not None:
                search_locations = parent_node.spec.submodule_search_locations
                if search_locations:
                    try:
                        return PathFinder.find_spec(fullname, list(search_locations))
                    except ModuleNotFoundError:
                        # See _make_namespace_spec(): namespace submodules
                        # whose parent is not imported cannot be resolved
                        # by PathFinder.
                        return self._make_namespace_spec(fullname, list(search_locations))
            # Parent unknown: walk up to the deepest known ancestor and
            # resolve the remaining chain component by component (e.g.
            # ``package.subpackage.sub`` when only the namespace ``package``
            # is in the graph: ``subpackage`` is found inside ``package``'s
            # search locations, then ``sub`` inside ``subpackage``'s).
            spec = self._resolve_submodule_chain(fullname)
            if spec is not None:
                return spec
            # Last resort: documented fallback (imports the parent).
            try:
                return importlib_util.find_spec(fullname)
            except (ImportError, SyntaxError, ValueError):
                return None

        # Top-level module: PathFinder over the graph's search path first,
        # so real files shadow frozen/builtin entries of the same name.
        spec = PathFinder.find_spec(fullname, self.path)
        if spec is None:
            spec = FrozenImporter.find_spec(fullname)
        if spec is None:
            # BuiltinImporter raises ValueError for dotted names, hence the
            # top-level-only placement of this branch.
            spec = BuiltinImporter.find_spec(fullname)
        return spec

    # ------------------------------------------------------------------
    # Bytecode scanning
    # ------------------------------------------------------------------

    @staticmethod
    def _scan_code(code: CodeType) -> "Iterator[Union[Tuple[str, int, tuple], Set[str]]]":
        """
        Scan compiled bytecode for imports and defined names.

        Yields, in order:

        * one ``(module_name, level, fromlist)`` tuple per ``IMPORT_NAME``
          instruction found -- including inside nested functions and classes
          (their code objects are constants of the enclosing code object, so
          they are walked recursively);
        * finally, a ``set`` of all top-level names the code defines
          (``STORE_NAME``/``STORE_GLOBAL`` minus ``DELETE_NAME``/
          ``DELETE_GLOBAL``), which the package handling uses to tell
          "name defined by ``__init__.py``" apart from "name that must be a
          submodule".

        Instructions are matched by *name* (``inst.opname``) rather than raw
        opcode numbers: opcodes are CPython-version specific, names are part
        of the documented ``dis`` module API
        (https://docs.python.org/3/library/dis.html). This also avoids the
        class of ``AssertionError`` bugs the old scanner had around opcode
        sequence assumptions (issues #5525, #7055).
        """
        # Code objects to scan; ``root`` marks the module's own top-level
        # code, whose STORE_NAME instructions define module attributes.
        objects: "deque[Tuple[bool, CodeType]]" = deque()
        objects.append((True, code))
        names: Set[str] = set()

        while objects:
            root, obj = objects.popleft()

            # -- The import operands ------------------------------------------
            #
            # Bytecode layout of an import statement: the IMPORT_NAME
            # instruction is *always* immediately preceded by two
            # instructions that push the operands of ``__import__()``:
            #
            #     <push> <level>       relative-import depth: 0 = absolute,
            #     <push> <fromlist>    None for plain ``import x``, a tuple
            #                          for ``from x import a, b``, ('*',)
            #                          for ``from x import *``
            #     IMPORT_NAME <name>
            #
            # This layout is guaranteed by the compiler (it is how the
            # IMPORT_NAME opcode is defined), so instead of trying to
            # recognise "constant loading" instructions by name we simply
            # remember the operand values of the two most recent
            # instructions -- of any kind -- and read them off whenever
            # IMPORT_NAME shows up.
            #
            # Why not match ``LOAD_CONST`` by name? Because CPython 3.14
            # split that opcode into several specialised ones
            # (LOAD_SMALL_INT, LOAD_NONE, LOAD_TRUE, LOAD_FALSE,
            # LOAD_CONST_MORTAL, LOAD_CONST_IMMORTAL, ...). Name matching
            # would then silently miss the real operands and pick up
            # unrelated constants instead -- e.g. a module docstring --
            # producing garbage like ``level='docstring'``. The
            # two-instructions-before-IMPORT_NAME layout, by contrast, has
            # been stable across every CPython release so far.
            loads: "deque" = deque(maxlen=2)
            for inst in dis.get_instructions(obj):
                if inst.opname == 'IMPORT_NAME':
                    # In the case of a star import, fromlist will be ('*',).
                    # Unpack *before* appending the current instruction, or
                    # ``fromlist`` would read the module's own name off the
                    # deque (the deque is meant to hold the two instructions
                    # preceding IMPORT_NAME, not IMPORT_NAME itself).
                    level, fromlist = loads
                    # Normalize ``None`` (plain ``import x``) to an empty tuple so downstream
                    # code can always iterate ``fromlist`` without a None check.
                    yield inst.argval, level, fromlist or ()
                elif inst.opname in ('EXTENDED_ARG', 'NOP'):
                    # Pseudo-instructions that modify the following instruction's operand or are pure
                    # placeholders (Python 3.15 emits ``EXTENDED_ARG`` between the level/fromlist pushes and
                    # IMPORT_NAME whenever the module-name operand is large; ``NOP`` shows up around
                    # specialized code on newer CPython). Neither touches the value stack, so they must
                    # not be counted as import operands.
                    continue
                elif root and inst.opname in ('STORE_NAME', 'STORE_GLOBAL'):
                    names.add(inst.argval)
                elif root and inst.opname in ('DELETE_NAME', 'DELETE_GLOBAL'):
                    # discard: deleting an undefined name is legal at the
                    # bytecode level (e.g. ``del`` inside a try block).
                    names.discard(inst.argval)
                loads.append(inst.argval)

            # Functions and classes are compiled to code objects stored as
            # constants of their enclosing code object; imports inside them
            # count too.
            for const in obj.co_consts:
                if isinstance(const, CodeType):
                    objects.append((False, const))

        yield names

    # ------------------------------------------------------------------
    # The analysis loop
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """
        Drain the work queue, resolving and scanning every queued module.

        This is the heart of the engine. See the class docstring for the
        big picture; the per-item pipeline is:

        1.  skip if already in the graph (but still draw the edge and honor
            a ``from``-list the earlier processing did not see),
        2.  skip if excluded,
        3.  skip if an ``excludedimports`` rule from the importer's hook
            suppresses it (PyInstaller hook machinery only),
        4.  run the ``pre_safe_import_module`` hook, which may register
            runtime modules/aliases or rewrite the module name (hooks only),
        5.  honor the ``implies`` mapping (aliases, untrackable imports),
        6.  resolve with :meth:`_find_spec`; failure -> MISSING node,
        7.  classify by spec (builtin / frozen / namespace / extension /
            source / bytecode) and create the node exactly once,
        8.  compile + scan the code, queueing every import found.
        """
        while self._queue:
            self._process_queue_item(self._queue.popleft())

    def _process_queue_item(self, item: QueueItem) -> None:
        """Process a single work-queue item. See :meth:`_run`."""
        # -- 1: already in the graph? --
        existing = self.nodes.get(item.name)
        if existing is not None:
            if item.importing_module:
                self.add_edge(item.importing_module, item.name)
            # If this import site has a from-list that the earlier processing
            # did not know about, make sure its submodules still get queued.
            if item.fromlist and existing.module_type in (ModuleType.PACKAGE, ModuleType.NAMESPACE):
                self._queue_package_fromlist(item, existing)
            return

        # -- 2: excluded? --
        if item.name in self.excludes:
            return

        # -- 3: hook-declared excluded imports? --
        # Only meaningful when the hook machinery is active (hooks is not
        # None); standalone graphs have no exclusion rules.
        if item.importing_module and self._hooks is not None:
            if self._check_excluded_import(item.importing_module, item.name):
                self.msg(2, "Suppressing import of %r from module %r due to excludedimports", item.name,
                         item.importing_module)
                return

        # -- 4: pre-safe-import-module hook --
        if self._hooks_pre_safe_import_module is not None:
            item = self._run_pre_safe_import_hook(item)

        # -- 5: implied dependencies (C-level imports, aliases, ...) --
        if item.name in self._implies:
            implied = self._implies.pop(item.name)
            if isinstance(implied, Alias):
                # The name is an alias for another module (e.g. os.path ->
                # ntpath): create the alias node and analyze the real module
                # instead of the (non-resolvable) alias name.
                self._add_node(item.name, ModuleType.ALIAS, target=str(implied))
                if item.importing_module:
                    self.add_edge(item.importing_module, item.name)
                self._queue_import(str(implied), item.name)
                return
            if implied is None:
                # The module exists but its imports are untrackable (e.g.
                # _frozen_importlib is part of the interpreter): record the
                # node, skip the scan. Falls through to normal resolution.
                scan_disabled = True
                pending_implies = None
            else:
                scan_disabled = False
                pending_implies = implied
        else:
            scan_disabled = False
            pending_implies = None

        # -- 6: resolve --
        spec = self._find_spec(item.name)
        if spec is None and not item.is_script:
            self._add_node(item.name, ModuleType.MISSING)
            if item.importing_module:
                self.add_edge(item.importing_module, item.name)
            return

        # -- 7: classify and create the node (exactly once!) --
        node = self._create_node(item, spec)
        if item.importing_module:
            self.add_edge(item.importing_module, item.name)

        # -- 8: scan --
        if node is not None and not scan_disabled and node.code is not None:
            self._process_node_imports(item, node)

        # Queue implied dependencies recorded for this module.
        if pending_implies:
            for implied_name in pending_implies:
                self._queue_import(implied_name, item.name)

    # ------------------------------------------------------------------
    # Node creation and classification
    # ------------------------------------------------------------------

    def _create_node(self, item: QueueItem, spec: Optional[ModuleSpec]) -> Node:
        """
        Classify a resolved module and insert its node into the graph.

        Classification follows the spec the finders produced: ``origin``
        tells builtins/frozen apart, a ``None`` origin with search locations
        means a namespace package, and everything else is classified by file
        suffix using importlib's documented suffix constants
        (``SOURCE_SUFFIXES``, ``EXTENSION_SUFFIXES``, ...).

        :return: The created (and already inserted) node.
        """
        existing = self.nodes.get(item.name)
        if existing is not None:
            # A node for this name may have been created while the
            # pre-safe-import-module hook was running (e.g. by
            # ``alias_module()``, which can route this very queue item
            # through the alias machinery). Never clobber it with a
            # real module node.
            return existing

        if item.is_script:
            # Scripts carry their path; compile directly.
            code = compile(Path(item.path).read_bytes(), str(item.path), "exec")
            node = Node(ident=item.name, module_type=ModuleType.SCRIPT, path=str(item.path), code=code)
            self.nodes[item.name] = node
            return node

        origin = spec.origin
        if origin == 'built-in':
            node = self._add_node(item.name, ModuleType.BUILTIN, spec=spec)
        elif origin == 'frozen':
            # Frozen modules (interpreter-provided) have no source to scan.
            node = self._add_node(item.name, ModuleType.FROZEN, spec=spec)
        elif origin is None and spec.submodule_search_locations is not None:
            # No file, but search locations: PEP 420 namespace package.
            node = self._add_node(item.name, ModuleType.NAMESPACE, spec=spec)
        else:
            module_path = Path(origin).resolve()

            if isinstance(spec.loader, zipimport.zipimporter):
                # Entry inside a zip archive (egg/wheel): pathlib cannot open
                # it, so the loader is the only way to the source. Note that
                # zipimporter may point the spec's origin at either the .py
                # or the .pyc entry, so classification must not rely on the
                # file suffix.
                try:
                    code = spec.loader.get_code(item.name)
                except SyntaxError:
                    # The module cannot be parsed. Gracefully skip it rather
                    # than crashing the whole graph-building process.
                    return None
                module_type = ModuleType.PACKAGE if module_path.stem == '__init__' else ModuleType.PURE
            elif module_path.suffix in importlib_machinery.SOURCE_SUFFIXES:
                # __init__.py marks a package root; its relative imports and
                # from-import fallbacks resolve against the package itself.
                if module_path.stem == '__init__':
                    module_type = ModuleType.PACKAGE
                else:
                    module_type = ModuleType.PURE
                try:
                    code = compile(module_path.read_bytes(), str(module_path), "exec")
                except SyntaxError:
                    # The module cannot be parsed. Gracefully skip it rather
                    # than crashing the whole graph-building process.
                    return None
            elif module_path.suffix in importlib_machinery.BYTECODE_SUFFIXES and isinstance(
                spec.loader, importlib_machinery.SourcelessFileLoader
            ):
                # Pre-compiled bytecode-only module; reading the code object
                # from the loader saves a compile pass.
                module_type = ModuleType.BYTECODE
                try:
                    code = spec.loader.get_code(item.name)
                except Exception:
                    return None
            elif module_path.suffix in importlib_machinery.EXTENSION_SUFFIXES:
                # Extension module: a graph leaf, nothing to analyze.
                return self._add_node(item.name, ModuleType.EXTENSION, path=str(module_path), spec=spec)
            else:
                raise ValueError(f"Unknown file suffix for importable module: {module_path}")

            node = Node(
                ident=item.name,
                module_type=module_type,
                path=str(module_path),
                spec=spec,
                code=code,
            )
            self.nodes[item.name] = node

        return node

    def _add_node(
        self,
        ident: str,
        module_type: ModuleType,
        *,
        path: Optional[str] = None,
        spec: Optional[ModuleType] = None,
        target: Optional[str] = None,
        code: Optional[CodeType] = None,
    ) -> Node:
        """
        Create a node and insert it into the graph.

        The single insertion point for node creation (besides scripts and
        runtime modules, which build nodes directly), guaranteeing that
        every node in :attr:`nodes` is created exactly once.
        """
        node = Node(ident=ident, module_type=module_type, path=path, spec=spec, target=target, code=code)
        self.nodes[ident] = node
        return node

    # ------------------------------------------------------------------
    # Import bookkeeping
    # ------------------------------------------------------------------

    def _process_node_imports(self, item: QueueItem, node: Node) -> None:
        """
        Scan a node's code and queue everything it imports.

        Relative imports are resolved against the enclosing package using
        ``importlib.util.resolve_name()`` per its documentation
        (https://docs.python.org/3/library/importlib.html#importlib.util.resolve_name).
        The parent for resolution is the node's spec parent -- except for
        ``__init__.py`` files, whose relative imports resolve against the
        package *itself*.
        """
        assert node.code is not None

        # Parent package for relative-import resolution.
        if node.spec is not None and node.spec.parent:
            parent = node.spec.parent
        elif node.module_type == ModuleType.PACKAGE:
            parent = item.name
        else:
            parent = None

        provided_names: Set[str] = set()
        for data in self._scan_code(node.code):
            if isinstance(data, set):
                # The trailing "defined names" yield.
                provided_names = data
                continue

            name, level, fromlist = data
            try:
                resolved_name = importlib_util.resolve_name(f"{'.' * level}{name}", parent)
            except ImportError:
                self.msg(2, "Invalid relative import %r (level %d) in module %r", name, level, item.name)
                continue

            # ``from package import submodule``: hand the from-list to the
            # package so its submodules get queued (see
            # _queue_package_fromlist); the package itself is queued here.
            self._queue_import(resolved_name, item.name, fromlist=fromlist)

        # Record the names this module's own code defines, so later
        # ``from package import name`` statements can tell package attributes
        # apart from submodules.
        node.provided_names = provided_names

        # A package's ``__init__.py`` often relies on submodule imports
        # performed by its *users* ("from pkg import thing"): anything the
        # from-list named that the package itself does not define must be a
        # submodule, and needs to enter the graph (issue #2437).
        if node.module_type == ModuleType.PACKAGE:
            self._queue_package_fromlist(item, node, provided_names)

    def _queue_package_fromlist(self, item: QueueItem, package_node: Node, provided_names: Optional[Set[str]] = None):
        """
        Queue the submodules a ``from package import x`` statement named.

        Used both when the package is processed fresh and when it was already
        in the graph (in which case the earlier processing never saw this
        particular from-list). Names the package's own code defines are plain
        attributes, not submodules, and are skipped -- chasing them would
        fabricate MISSING nodes for things like ``collections.OrderedDict``.
        """
        if provided_names is None:
            # Package already analyzed: reuse the names recorded during its
            # own scan (namespace packages have no code and thus an empty
            # set, which is correct -- every from-list entry of a namespace
            # package must be a submodule).
            provided_names = package_node.provided_names

        for attr_name in item.fromlist:
            if attr_name in ('', '*'):
                continue
            try:
                submodule_name = importlib_util.resolve_name(f".{attr_name}", package_node.ident)
            except ImportError:
                continue
            if attr_name in provided_names:
                # The package's own code also binds this name as a global
                # attribute (e.g. ``from collections import OrderedDict``).
                # Python semantics resolve it to the attribute, so chasing it
                # would fabricate MISSING nodes -- unless a real submodule of
                # the same name exists on disk (``from . import logging`` in
                # setuptools). Old modulegraph attempted the submodule import
                # first and only fell back to treating the name as an
                # ignorable attribute when it was unimportable; do the same.
                if self._find_spec(submodule_name) is None:
                    continue
            self._queue_import(submodule_name, package_node.ident)

    def _queue_import(
        self,
        name: str,
        importing_module: Optional[str],
        fromlist: tuple = (),
        level: int = 0,
    ) -> None:
        """
        Append an import to the work queue.

        Single funnel for every queued import. For dotted names, the parent
        packages are queued first (without a from-list, which belongs to the
        full name only) so that:
        * submodule resolution can use the parent's search locations
          instead of falling back to a real import of the parent, and
        * the parent packages stay reachable from the graph roots -- they
          must be collected into the bundle even though nothing imports
          them directly.
        """
        parts = name.split('.')
        for depth in range(1, len(parts)):
            parent_name = '.'.join(parts[:depth])
            self._queue.append(QueueItem(name=parent_name, importing_module=importing_module))

        self._queue.append(
            QueueItem(name=name, importing_module=importing_module, fromlist=tuple(fromlist), import_level=level)
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_arg(self, arg: "Union[str, Node]", required: bool = True) -> Optional[Node]:
        """
        Accept either a node name or a node object and return the node.

        With ``required`` set, a missing node raises ``ValueError``; with it
        unset, ``None`` is returned (used by the edge methods, which drop
        dangling references).
        """
        if isinstance(arg, Node):
            name = arg.ident
        else:
            name = arg
        node = self.nodes.get(name)
        if node is None and required:
            raise ValueError(f"Node {name!r} does not exist in the graph!")
        return node

    # ------------------------------------------------------------------
    # Reports: HTML cross-reference and Graphviz DOT output
    # ------------------------------------------------------------------

    def create_xref(self, fh: TextIO) -> None:
        """
        Write an HTML cross-reference of the graph to *fh*.

        Every node becomes one HTML entry, listing the modules it imports
        ("imports") and the modules that import it ("imported by"), with
        anchors linking each name to its own entry. Nodes are sorted by the
        basename of their :attr:`~.nodes.Node.ident`; scripts are listed
        first, followed by the modules.
        """
        scripts = []
        mods = []
        for mod in self.iter_graph():
            name = os.path.basename(mod.ident)
            if mod.module_type == ModuleType.SCRIPT:
                scripts.append((name, mod))
            else:
                mods.append((name, mod))
        scripts.sort()
        mods.sort()
        scriptnames = [sn for sn, m in scripts]
        scripts.extend(mods)
        mods = scripts

        title = "modulegraph cross reference for " + ', '.join(scriptnames)
        print(header % {"TITLE": title}, file=fh)

        for name, mod in mods:
            if mod.module_type == ModuleType.BUILTIN:
                content = contpl % {"NAME": name, "TYPE": "<i>(builtin module)</i>"}
            elif mod.module_type == ModuleType.EXTENSION:
                content = contpl % {"NAME": name, "TYPE": "<tt>%s</tt>" % mod.path}
            else:
                url = pathname2url(mod.path or "")
                content = contpl_linked % {"NAME": name, "URL": url, "TYPE": mod.module_type.value}

            # `dependencies` are the modules this node imports ("outgoing"),
            # `importing_modules` the modules that import it ("incoming").
            oute = sorted(os.path.basename(n) for n in mod.dependencies)
            ince = sorted(os.path.basename(n) for n in mod.importing_modules)
            for head, names in (("imports", oute), ("imported by", ince)):
                if not names:
                    continue
                # &#8226; = bullet-point; can't use html-entities since the
                # test-suite uses xml.etree.ElementTree.XMLParser, which
                # doesn't support them.
                links = " &#8226; ".join(f'  <a href="#{n}">{n}</a>\n' for n in names)
                content += imports % {"HEAD": head, "LINKS": links}

            print(entry % {"NAME": name, "CONTENT": content}, file=fh)
        print(footer, file=fh)

    def itergraphreport(self, name: str = 'G') -> "Iterator[str]":
        """
        Generate a Graphviz DOT representation of the graph, one line at a
        time.

        The output is a ``digraph`` in left-to-right layout: one record-style
        node per graph node (labelled with the node's type and name) and one
        edge per import relationship.
        """
        yield 'digraph %s {\ncharset="UTF-8";\n' % (name,)
        yield '\trankdir="LR";\n'
        yield '\tconcentrate="true";\n'

        def node_label(node: Node) -> str:
            # ModuleType.SPECIAL's value is None (placeholder root); use the
            # enum member name as a readable fallback.
            type_name = node.module_type.value if node.module_type.value is not None else node.module_type.name
            s = '<f0> ' + type_name
            s += '| <f1> %s' % (node.ident,)
            return {'label': s, 'shape': 'record'}

        for node in self.iter_graph():
            # describe node
            yield '\t"%s" [%s];\n' % (
                node.ident,
                ','.join((f'{key}="{value}"' for key, value in node_label(node).items())),
            )

        # describe edges; importers -> imported
        for node in self.iter_graph():
            for dependency in node.dependencies:
                yield '\t"%s" -> "%s";\n' % (node.ident, dependency)

        yield '}\n'

    def graphreport(self, fh: TextIO) -> None:
        """
        Write a Graphviz DOT representation of the graph to *fh*.
        """
        fh.writelines(self.itergraphreport())

    def __repr__(self):
        return f"<ModuleGraph: {len(self.nodes)} nodes>"


def _ident_of(arg: "Union[str, Node, None]") -> Optional[str]:
    """
    Return the node name for a node-or-name argument (or None).
    """
    if arg is None:
        return None
    if isinstance(arg, Node):
        return arg.ident
    return arg


# ------------------------------------------------------------------------------
# The one entry point PyInstaller's build driver uses
# ------------------------------------------------------------------------------

# Cache for the "base" module graph (the graph of PyInstaller's own bootstrap
# modules, i.e. everything inside ``base_library.zip`` plus the standard-library
# modules every program needs). Every build starts from this graph, and building
# it requires scanning a few hundred modules -- which took a noticeable slice of
# the test-suite runtime when every test-case did it from scratch. Caching one
# pristine graph and handing each caller a deep copy turned that from
# "re-scan per test" into "copy per test" (deepcopy of a graph is far cheaper
# than analyzing it), which is why this module-global exists at all. It is
# deliberately NOT thread-safe: builds and tests are single-threaded.
_cached_module_graph_: Optional["ModuleGraph"] = None


def initialize_modgraph(excludes: Tuple[str, ...] = (), user_hook_dirs=()) -> "ModuleGraph":
    """
    Create the module graph that every build (and test) starts from.

    This is the former ``PyInstaller.depend.analysis.initialize_modgraph``.
    It builds the *base* graph -- the standard-library modules that
    ``base_library.zip`` must contain plus the hook machinery -- and either
    returns a fresh graph or a deep copy of a previously-cached one.

    Why the cache? Creating the base graph means analyzing several hundred
    standard-library modules. The test-suite calls this function for nearly
    every test-case, and (mostly) with the same ``excludes``; caching the
    first graph and deep-copying it for later calls is dramatically faster
    than re-analyzing. Production builds call it once per build, so they pay
    for exactly one graph creation.

    Parameters
    ----------
    excludes : tuple of str
        Fully-qualified names of modules that must never enter the graph
        (nor be frozen into the executable). Merged with ``__main__``, see
        below.
    user_hook_dirs : iterable of (path, priority) tuples
        Extra directories containing user-defined hooks, ordered by
        priority. May be empty; the built-in hook directory is always
        appended internally by :meth:`ModuleGraph._setup_hooks`.

    Returns
    -------
    ModuleGraph
        A graph seeded with the base modules, ready for ``add_script()``.
    """
    global _cached_module_graph_

    # Normalize parameters so cache comparison and set operations work
    # regardless of whether callers passed lists, tuples, or None.
    user_hook_dirs = tuple(user_hook_dirs or ())
    excludes = tuple(excludes or ())

    # Always exclude "__main__" from the graph. During *analysis* the name
    # refers to the build-time entry point of PyInstaller's own executable
    # (e.g. ``.../PyInstaller.exe/__main__.py`` on Windows); without this
    # exclusion the graph can accidentally pull PyInstaller itself into the
    # bundle. At *run-time* "__main__" is the frozen program's entry-point,
    # which is always part of the graph as the script node anyway.
    if "__main__" not in excludes:
        excludes += ("__main__",)

    # If a graph was cached with the same excludes, reuse it: hand back a
    # deep copy and rebuild only the hook state, which is per-analysis (see
    # _setup_hooks: it re-reads hook directories and re-creates the hook
    # caches). The node graph -- base modules and their edges -- is
    # identical between calls with the same excludes, so copying it is safe.
    if _cached_module_graph_ is not None and _cached_module_graph_.excludes == set(excludes):
        logger.info('Reusing cached module dependency graph...')
        graph = deepcopy(_cached_module_graph_)
        graph._setup_hooks(user_hook_dirs)
        return graph

    logger.info('Initializing module dependency graph...')

    # Construct the initial module graph by analyzing all import statements
    # reachable from the standard-library base modules (see
    # ModuleGraphHooks._analyze_base_modules for exactly what gets scanned).
    # ``get_implies()`` supplies the curated list of hidden imports -- modules
    # that are loaded behind PyInstaller's back (from C extension code, the
    # frozen import system, etc.) and are therefore invisible to bytecode
    # scanning but must still be collected.
    graph = ModuleGraph(
        pyi_homepath=HOMEPATH,
        excludes=excludes,
        implies=get_implies(),
        user_hook_dirs=user_hook_dirs,
    )

    if _cached_module_graph_ is None:
        # Only the first graph is cached (see the function docstring for why).
        logger.info('Caching module dependency graph...')
        _cached_module_graph_ = deepcopy(graph)
        # Drop the hook caches from the cached copy: they are rebuilt from
        # scratch by _setup_hooks() on every reuse, and keeping them would
        # pin every hook file's ModuleHook object in memory for nothing.
        _cached_module_graph_._hooks = None
        _cached_module_graph_._hooks_pre_safe_import_module = None
        _cached_module_graph_._hooks_pre_find_module_path = None

    return graph
