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
The data model for the module graph.

This module answers one question: "what *is* a thing in the dependency graph?"

Everything PyInstaller discovers while analyzing a program becomes a
:class:`Node` stored in the graph. Every node carries:

* ``ident`` -- the node's name. For modules and packages this is the
  fully-qualified import name (``os.path``, ``requests.api``); for scripts it
  is the absolute path of the ``.py`` file.
* ``module_type`` -- which :class:`ModuleType` the node is. Think of the old
  ``modulegraph`` package, where every kind of module was its own Python class
  (``SourceModule``, ``Package``, ``BuiltinModule``, ...). Here those same
  kinds are enum members instead, so a single small dataclass covers them all.
* ``path`` -- the on-disk file backing the node, when one exists.
* ``spec`` -- the :class:`importlib.machinery.ModuleSpec` that importlib's
  finders produced for the node. The spec is the authoritative record of
  *how* Python would import this thing (which loader, which search
  locations, ...), so we keep it instead of duplicating that information.
* ``code`` -- the compiled bytecode (a ``code`` object) for pure Python
  nodes. PyInstaller freezes this bytecode, so keeping it here saves a second
  compile later.
* ``importing_modules`` / ``dependencies`` -- the two ends of the graph
  edges. Each is a set of *node names* (not node objects) so that the graph
  is trivially serializable and cycle-safe. ``dependencies`` are the modules
  this node imports ("outgoing" edges); ``importing_modules`` are the modules
  that import this node ("incoming" edges).

If you are reading PyInstaller's analysis code for the first time, start
here: every other module in this package manipulates the objects defined
below.
"""

# We rely on PEP 563 ("from __future__ import annotations") so that annotations
# such as ``Optional[ModuleSpec]`` are stored as strings rather than evaluated
# at class-creation time. This keeps the dataclass definitions cheap and lets
# us reference types that only exist for the benefit of type-checkers.
from __future__ import annotations

import dataclasses
from enum import Enum

from importlib.machinery import ModuleSpec

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import CodeType
    from typing import Dict, Optional, Set

    # ``os.PathLike`` is generic only from Python 3.9 onward; PyInstaller
    # still supports Python 3.8 (see ``requires-python`` in setup.cfg), so we
    # annotate paths as plain ``str``-likes without subscripting it.
    from typing import Union


class ModuleType(Enum):
    """
    The kind of thing a :class:`Node` represents.

    The ``value`` of every member is the name of the corresponding node class
    in the legacy (pre-rewrite) ``modulegraph`` package. Keeping the old
    strings as the enum values makes debug output, warnings and the TOC
    mappings recognizable to anyone who has ever read a PyInstaller build log
    ("SourceModule", "Package", ...), and lets us translate from the old
    string-based type sets in ``PyInstaller.compat`` without a lookup table.
    """

    # A placeholder node that exists only so the graph always has a root.
    # The first script added to the graph takes over as the real root; the
    # placeholder is never frozen or collected.
    SPECIAL = None

    # A module provided by the interpreter itself (e.g. one baked into the
    # frozen importer, or a module registered with PyInstaller's own frozen
    # importer at run time). These have no on-disk source to analyze.
    FROZEN = "FrozenModule"

    # A pure-Python module whose file is named ``__init__.py`` -- i.e. the
    # root file of a (regular, non-namespace) package. Packages get their own
    # type because their imports resolve relative to the package itself and
    # because "from package import name" may need to fall back to treating
    # *name* as a submodule of the package.
    PACKAGE = "Package"

    # An ordinary pure-Python module: a ``.py`` file that is not an
    # ``__init__.py`` and not a script.
    PURE = "SourceModule"

    # A PEP 420 implicit namespace package: a directory that contributes to a
    # package name but contains no ``__init__.py``. Its only meaningful data
    # is the list of search locations (``spec.submodule_search_locations``).
    NAMESPACE = "NamespacePackage"

    # A compiled C/Cython extension (``.pyd`` on Windows, ``.so`` elsewhere).
    # Extension modules cannot be analyzed further -- there is no Python
    # bytecode to scan -- so they are graph leaves.
    EXTENSION = "ExtensionModule"

    # A module that could not be found at all. Keeping these as real nodes
    # (rather than dropping them) lets us warn about them, name the modules
    # that tried to import them, and write them to build warnings.
    MISSING = "MissingModule"

    # A non-importable script: the program's entry point (or a run-time hook).
    # Scripts are graph roots -- nothing imports them, they import others --
    # and PyInstaller freezes them by file path, not by module name.
    SCRIPT = "Script"

    # A module compiled into the interpreter itself (``sys.builtin_module_names``),
    # exposed through ``importlib.machinery.BuiltinImporter``. Needs no file.
    BUILTIN = "BuiltinModule"

    # A module provided as pre-compiled bytecode (``.pyc``) without
    # accompanying source, loaded through ``SourcelessFileLoader``.
    BYTECODE = "BytecodeModule"

    # Modules and packages that exist only at run time -- they are created by
    # executing code (e.g. ``six.moves``), not by importing a file. Hooks
    # declare these via ``pre_safe_import_module()`` hooks so that the graph
    # knows where "from six.moves import queue" should lead.
    RUNTIME_MODULE = "RuntimeModule"
    RUNTIME_PACKAGE = "RuntimePackage"

    # An alias node: a name that stands in for another module. Importing the
    # alias behaves like importing the target (e.g. ``os.path`` is an alias
    # for ``ntpath``/``posixpath`` depending on the platform).
    ALIAS = "Alias"


@dataclasses.dataclass
class Node:
    """
    One vertex of the module dependency graph.

    See the module docstring for a walk-through of the individual fields.
    Nodes compare and hash purely by their ``ident``: there is exactly one
    node per module name (or script path) in a graph, and passing the same
    name around never creates a second node.
    """

    # The node's name: a fully-qualified module name, or an absolute script
    # path for :attr:`ModuleType.SCRIPT` nodes.
    ident: str

    # Which kind of thing this node is. See :class:`ModuleType`.
    module_type: ModuleType

    # Absolute path of the file backing this node, if it has one. ``None``
    # for builtins, missing modules and scripts that were added by name.
    path: Optional[str] = None

    # The importlib ModuleSpec describing how this node is imported. Kept
    # verbatim from the finder so we never re-derive search locations.
    spec: Optional[ModuleSpec] = None

    # The compiled code object of a pure-Python node; ``None`` for anything
    # that is not analyzable bytecode (extensions, builtins, missing, ...).
    code: Optional[CodeType] = None

    # For :attr:`ModuleType.ALIAS` nodes: the name of the module this alias
    # stands in for.
    target: Optional[str] = None

    # Names defined by the node's own top-level code (from the bytecode
    # scan's STORE_NAME/STORE_GLOBAL tracking). Meaningful for packages:
    # when a ``from package import name`` statement names something the
    # package's ``__init__.py`` does *not* define, that name must be a
    # submodule and enters the graph as one. This avoids chasing plain
    # attributes (e.g. ``collections.OrderedDict``) as phantom submodules.
    provided_names: Set[str] = dataclasses.field(default_factory=set)

    # Names of the nodes that import this node ("incoming" edges).
    importing_modules: Set[str] = dataclasses.field(default_factory=set)

    # Names of the nodes this node imports ("outgoing" edges).
    dependencies: Set[str] = dataclasses.field(default_factory=set)

    def __eq__(self, other):
        # Nodes are identified by name alone; two nodes with the same ident
        # *are* the same node. Returning ``NotImplemented`` (rather than
        # ``False``) for foreign types lets Python fall back to the other
        # object's comparison, per the data model documented at
        # https://docs.python.org/3/reference/datamodel.html#object.__eq__
        if not isinstance(other, Node):
            return NotImplemented
        return self.ident == other.ident

    def __hash__(self):
        return hash(self.ident)

    def __repr__(self):
        return f"<Node {self.ident} ({self.module_type})>"


@dataclasses.dataclass
class QueueItem:
    """
    A single unit of work for the graph's analysis queue.

    The graph does not recurse: when module A imports module B, the graph
    appends a :class:`QueueItem` describing B to a deque and keeps scanning A
    (or whatever else is next in line). This is what makes the rewrite immune
    to the ``RecursionError`` storms that plagued the old, recursive
    modulegraph (see upstream issues #2875, #2911, #3040, #3752 and friends).

    Fields
    ------
    name
        Fully-qualified name of the module to resolve, or the absolute path
        of a script (when ``is_script`` is true).
    path
        For scripts only: the path of the script file.
    importing_module
        Name of the module whose import statement caused this item to be
        queued; the graph draws the edge importer -> imported once the item
        is processed. ``None`` for graph roots (scripts, base modules).
    import_level
        The relative-import level of the originating ``import`` statement
        (0 for absolute imports, 1 for ``from . import x``, ...). Kept for
        diagnostics; resolution happens when the import is queued.
    is_script
        Whether ``name`` is a script path rather than a module name.
    fromlist
        The ``from module import a, b`` names associated with this import.
        For package nodes these may name submodules that need to be queued.
    """

    # Fully-qualified name of the module (or script path) to process.
    name: str

    # Absolute path of the script file, for script items only.
    path: Optional[str] = None

    # Name of the importing module, or None for graph roots.
    importing_module: Optional[str] = None

    # Relative-import level of the originating import statement.
    import_level: int = 0

    # True when ``name`` is a script path rather than a module name.
    is_script: bool = False

    # Names imported via ``from <name> import <fromlist...>``.
    fromlist: tuple = ()


class Alias(str):
    """
    Marker for "this name is an alias for another module".

    Subclassing ``str`` (rather than being a plain string) lets
    ``PyInstaller.depend.modulegraph.implies.get_implies()`` return alias
    entries that the graph engine can distinguish from ordinary dependency
    lists, while still behaving like a string everywhere else. The
    ``str``-inheritance also keeps aliases marshalable, which matters
    because PyInstaller marshals TOC entries into the built executable.
    """


# ---------------------------------------------------------------------------
# Node-type classification sets
# ---------------------------------------------------------------------------
# The legacy ``PyInstaller.compat`` module classified nodes by the *name* of
# their old modulegraph class (strings such as ``'SourceModule'``). Since
# nodes now carry a :class:`ModuleType` enum, these classifications are
# rebuilt here, keyed by the enum itself. They drive TOC generation and the
# "is this node something we can actually freeze?" checks in the hook
# machinery.

# Pure Python modules: nodes that carry a compiled code object which
# PyInstaller can freeze directly into the PYZ archive.
PURE_PYTHON_MODULE_TYPES = {
    ModuleType.PURE,
    ModuleType.BYTECODE,
    ModuleType.PACKAGE,
    ModuleType.NAMESPACE,
}

# "Special" modules that are valid to collect but have no code object: the
# interpreter-provided modules, run-time-only modules and scripts. Alias
# nodes are deliberately omitted (as in the legacy classification) so that
# hooks do not run for the modules an alias points at.
SPECIAL_MODULE_TYPES = {
    ModuleType.BUILTIN,
    ModuleType.RUNTIME_MODULE,
    ModuleType.RUNTIME_PACKAGE,
    ModuleType.SCRIPT,
}

# Binary modules: compiled extensions collected as binaries rather than
# bytecode.
BINARY_MODULE_TYPES = {
    ModuleType.EXTENSION,
}

# Union of everything that is considered a real, collectable module.
VALID_MODULE_TYPES = PURE_PYTHON_MODULE_TYPES | SPECIAL_MODULE_TYPES | BINARY_MODULE_TYPES

# Nodes that exist in the graph for bookkeeping but represent nothing
# collectable: modules that were not found, and run-time-only modules that
# have no on-disk file to freeze.
BAD_MODULE_TYPES = {
    ModuleType.MISSING,
    ModuleType.RUNTIME_MODULE,
    ModuleType.RUNTIME_PACKAGE,
}

# Union of every node type the graph can ever produce: the valid, collectable
# module types plus the bad/missing bookkeeping ones. Useful for "is this a
# real node at all?" checks, e.g. when iterating debug TOCs that include
# every node in the graph.
ALL_MODULE_TYPES = VALID_MODULE_TYPES | BAD_MODULE_TYPES

# Mapping from each node type to the TOC typecode used in PyInstaller's
# internal (and marshalled) tables of contents. The typecodes -- 'PYSOURCE',
# 'PYMODULE', 'EXTENSION', ... -- are part of PyInstaller's serialized build
# format and must not change.
MODULE_TYPES_TO_TOC_DICT = {
    ModuleType.PURE: 'PYMODULE',
    ModuleType.BYTECODE: 'PYMODULE',
    ModuleType.PACKAGE: 'PYMODULE',
    ModuleType.NAMESPACE: 'PYMODULE',
    ModuleType.EXTENSION: 'EXTENSION',
    ModuleType.BUILTIN: 'BUILTIN',
    ModuleType.SCRIPT: 'PYSOURCE',
    ModuleType.ALIAS: 'PYMODULE',
    # Nodes that never end up in a TOC; mapped for completeness so that
    # debug/diagnostic TOCs (which include every node) never KeyError.
    ModuleType.MISSING: 'missing',
    ModuleType.RUNTIME_MODULE: 'runtime',
    ModuleType.RUNTIME_PACKAGE: 'runtime',
    ModuleType.FROZEN: 'frozen',
    ModuleType.SPECIAL: 'special',
}
