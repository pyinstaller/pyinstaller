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
Code related to processing of import hooks.

This module contains everything the hook system needs:

* :class:`ModuleHookCache` -- the per-graph registry of discoverable hook
  scripts (``hook-{module}.py`` files), keyed by hooked module name.
* :class:`ModuleHook` -- one lazily-loaded hook script.
* The three hook API classes (:class:`PreSafeImportModuleAPI`,
  :class:`PreFindModulePathAPI`, :class:`PostGraphAPI`) -- the objects
  PyInstaller passes *into* hook functions, through which hooks communicate
  their changes back to the graph.

The former ``imphookapi.py`` module was folded in here: the API classes are
inseparable from the hook machinery that constructs them, and the split only
existed for historical (circular-import) reasons.

Hook discovery of *entry-point* hook directories (the ``pyinstaller40`` /
``hook-dirs`` entry-point group) deliberately lives in
``PyInstaller.building.build_main.discover_hook_directories()`` and runs in
an isolated subprocess: loading an entry point imports the package that
declared it, and that must not happen in the analysis process.
"""

import glob
import os.path
import re
import sys
import weakref

from PyInstaller import log as logging
from PyInstaller.building.utils import format_binaries_and_datas
from PyInstaller.compat import importlib_load_source
from PyInstaller.exceptions import ImportErrorWhenRunningHook

logger = logging.getLogger(__name__)

# Hook priority constants. When several hook scripts exist for the same
# module (e.g. an upstream package ships its own hook while
# pyinstaller-hooks-contrib carries a fallback), the hook with the highest
# priority wins.
HOOK_PRIORITY_BUILTIN_HOOKS = -2000  # Built-in hooks. Lowest priority.
HOOK_PRIORITY_CONTRIBUTED_HOOKS = -1000  # Hooks from pyinstaller-hooks-contrib package.
HOOK_PRIORITY_UPSTREAM_HOOKS = 0  # Hooks provided by packages themselves, via entry-points.
HOOK_PRIORITY_USER_HOOKS = 1000  # User-supplied hooks (command-line / spec file). Highest priority.


class ModuleHookCache(dict):
    """
    Cache of lazily loadable hook script objects.

    This cache is implemented as a `dict` subclass mapping from the
    fully-qualified names of all modules with at least one hook script to
    lists of `ModuleHook` instances encapsulating these scripts. As a `dict`
    subclass, all cached module names and hook scripts are accessible via
    standard dictionary operations.

    Attributes
    ----------
    _hook_module_name_prefix : str
        String prefixing the names of all in-memory modules lazily loaded
        from cached hook scripts. See also the `hook_module_name_prefix`
        parameter passed to the `ModuleHook.__init__()` method.
    """

    # 0-based identifier unique to the next `ModuleHookCache` to be
    # instantiated.
    #
    # This identifier is incremented on each instantiation of a new
    # `ModuleHookCache` to isolate in-memory modules of lazily loaded hook
    # scripts in that cache to the same cache-specific namespace, preventing
    # edge-case collisions with existing in-memory modules in other caches.
    _cache_id_next = 0

    def __init__(self, module_graph, hook_dirs):
        """
        Cache all hook scripts in the passed directories.

        **Order of caching is significant** with respect to hooks for the
        same module, as the values of this dictionary are lists. Hooks for
        the same module will be run in the order in which they are cached.
        Previously cached hooks are always preserved rather than overridden.

        By default, official hooks are cached _before_ user-defined hooks.
        For modules with both official and user-defined hooks, this implies
        that the former take priority over and hence will be loaded _before_
        the latter.

        Parameters
        ----------
        module_graph : ModuleGraph
            Current module graph.
        hook_dirs : list
            List of ``(hook_directory, default_priority)`` tuples for all
            directories containing **hook scripts** (i.e., Python scripts
            with filenames matching ``hook-{module_name}.py``, where
            ``{module_name}`` is the module hooked by that script) to be
            cached.
        """
        super().__init__()

        # To avoid circular references and hence increased memory consumption,
        # a weak rather than strong reference is stored to the passed graph.
        # Since this graph is guaranteed to live longer than this cache, this
        # is guaranteed to be safe.
        self.module_graph = weakref.proxy(module_graph)

        # String unique to this cache prefixing the names of all in-memory
        # modules lazily loaded from cached hook scripts, privatized for
        # safety.
        self._hook_module_name_prefix = '__PyInstaller_hooks_{}_'.format(ModuleHookCache._cache_id_next)
        ModuleHookCache._cache_id_next += 1

        # Cache all hook scripts in the passed directories.
        self._cache_hook_dirs(hook_dirs)

    def _cache_hook_dirs(self, hook_dirs):
        """
        Cache all hook scripts in the passed directories.

        Parameters
        ----------
        hook_dirs : list
            List of ``(hook_directory, default_priority)`` tuples for all
            directories containing hook scripts to be cached.
        """

        for hook_dir, default_priority in hook_dirs:
            # Canonicalize this directory's path and validate its existence.
            hook_dir = os.path.abspath(hook_dir)
            if not os.path.isdir(hook_dir):
                raise FileNotFoundError('Hook directory "{}" not found.'.format(hook_dir))

            # For each hook script in this directory...
            hook_filenames = glob.glob(os.path.join(hook_dir, 'hook-*.py'))
            for hook_filename in hook_filenames:
                # Fully-qualified name of this hook's corresponding module,
                # constructed by removing the "hook-" prefix and ".py" suffix.
                module_name = os.path.basename(hook_filename)[5:-3]

                # Lazily loadable hook object.
                module_hook = ModuleHook(
                    module_graph=self.module_graph,
                    module_name=module_name,
                    hook_filename=hook_filename,
                    hook_module_name_prefix=self._hook_module_name_prefix,
                    default_priority=default_priority,
                )

                # Add this hook to this module's list of hooks.
                module_hooks = self.setdefault(module_name, [])
                module_hooks.append(module_hook)

        # Post-processing: we allow only one instance of hook per module.
        # Currently, the priority order is defined implicitly, via order of
        # hook directories, so the first hook in the list has the highest
        # priority.
        for module_name in self.keys():
            hooks = self[module_name]
            if len(hooks) == 1:
                self[module_name] = hooks[0]
            else:
                # Order by priority value, in descending order.
                sorted_hooks = sorted(hooks, key=lambda hook: hook.priority, reverse=True)
                self[module_name] = sorted_hooks[0]

    def remove_modules(self, *module_names):
        """
        Remove the passed modules and all hook scripts cached for these
        modules from this cache.

        Parameters
        ----------
        module_names : list
            List of all fully-qualified module names to be removed.
        """

        for module_name in module_names:
            # Unload this module's hook script modules from memory. Since
            # these are top-level pure-Python modules cached only in the
            # "sys.modules" dictionary, popping these modules from this
            # dictionary suffices to garbage collect them.
            module_hook = self.pop(module_name, None)  # Remove our reference, if available.
            if module_hook is not None:
                sys.modules.pop(module_hook.hook_module_name, None)


class PreSafeImportModuleAPI:
    """
    Metadata communicating changes made by the current **pre-safe import
    module hook** (i.e., hook run immediately _before_ a call to
    ``ModuleGraph``'s module resolution for the hooked module) back to
    PyInstaller.

    Pre-safe import module hooks _must_ define a ``pre_safe_import_module()``
    function accepting an instance of this class, whose attributes describe
    the module-resolution call creating the hooked module's graph node.

    Each pre-safe import module hook is run _only_ on the first attempt to
    create the hooked module's graph node and then subsequently ignored. If
    this hook successfully creates that graph node, the subsequent
    resolution will observe this fact and silently return without attempting
    to recreate that graph node.

    Pre-safe import module hooks are typically used to create graph nodes
    for **runtime modules** (i.e., modules dynamically defined at runtime).
    Most modules are physically defined in external ``.py``-suffixed
    scripts. Some modules, however, are dynamically defined at runtime
    (e.g., ``six.moves``, dynamically defined by the physically defined
    ``six.py`` module). However, the module graph only parses ``import``
    statements residing in external scripts; it is _not_ a full-fledged,
    Turing-complete Python interpreter and hence has no means of parsing
    ``import`` statements performed by runtime modules existing only
    in-memory.

    'With great power comes great responsibility.'

    Attributes (Immutable)
    ----------------------------
    The following attributes are **immutable** (i.e., read-only). For
    safety, any attempts to change these attributes _will_ result in a
    raised exception:

    module_graph : ModuleGraph
        Current module graph.
    parent_package : Node
        Graph node for the package providing this module _or_ `None` if
        this module is a top-level module.

    Attributes (Mutable)
    -----------------------------
    The following attributes are editable.

    module_basename : str
        Unqualified name of the module to be imported (e.g., `text`).
    module_name : str
        Fully-qualified name of this module (e.g., `email.mime.text`).
    """

    def __init__(self, module_graph, module_basename, module_name, parent_package):
        self._module_graph = module_graph
        self.module_basename = module_basename
        self.module_name = module_name
        self._parent_package = parent_package

    # Immutable properties. No corresponding setters are defined.
    @property
    def module_graph(self):
        """
        Current module graph.
        """
        return self._module_graph

    @property
    def parent_package(self):
        """
        Parent Package of this node.
        """
        return self._parent_package

    def add_runtime_module(self, module_name):
        """
        Add a graph node representing a non-package Python module with the
        passed name dynamically defined at runtime.

        Most modules are statically defined on-disk as standard Python
        files. Some modules, however, are dynamically defined in-memory at
        runtime (e.g., `gi.repository.Gst`, dynamically defined by the
        statically defined `gi.repository.__init__` module).

        This method adds a graph node representing such a runtime module.
        Since this module is _not_ a package, all attempts to import
        submodules from this module in ``from``-style import statements
        (e.g., the `queue` submodule in ``from six.moves import queue``)
        will be silently ignored. To circumvent this, simply call
        ``add_runtime_package()`` instead.

        Parameters
        ----------
        module_name : str
            Fully-qualified name of this module (e.g., `gi.repository.Gst`).

        Examples
        ----------
        This method is typically called by ``pre_safe_import_module()``
        hooks, e.g.::

            def pre_safe_import_module(api):
                api.add_runtime_module(api.module_name)
        """

        self._module_graph.add_runtime_module(module_name)

    def add_runtime_package(self, package_name):
        """
        Add a graph node representing a non-namespace Python package with
        the passed name dynamically defined at runtime.

        Most packages are statically defined on-disk as standard
        subdirectories containing ``__init__.py`` files. Some packages,
        however, are dynamically defined in-memory at runtime (e.g.,
        ``six.moves``, dynamically defined by the statically defined ``six``
        module).

        This method adds a graph node representing such a runtime package.
        All attributes imported from this package in ``from``-style import
        statements that are submodules of this package (e.g., the `queue`
        submodule in ``from six.moves import queue``) will be imported
        rather than ignored.

        Parameters
        ----------
        package_name : str
            Fully-qualified name of this package (e.g., `six.moves`).

        Examples
        ----------
        This method is typically called by ``pre_safe_import_module()``
        hooks, e.g.::

            def pre_safe_import_module(api):
                api.add_runtime_package(api.module_name)
        """

        self._module_graph.add_runtime_package(package_name)

    def add_alias_module(self, real_module_name, alias_module_name):
        """
        Alias the source module to the target module with the passed names.

        This method ensures that the next graph lookup given the target
        module name will resolve this alias. This includes importing and
        adding a graph node for the source module if needed as well as
        adding a reference from the target to the source module.

        Parameters
        ----------
        real_module_name : str
            Fully-qualified name of the **existing module** (i.e., the
            module being aliased).
        alias_module_name : str
            Fully-qualified name of the **non-existent module** (i.e., the
            alias to be created).
        """

        self._module_graph.alias_module(real_module_name, alias_module_name)

    def append_package_path(self, directory):
        """
        The module graph does a good job at simulating Python's import
        machinery, but it cannot handle package ``__path__`` modifications
        packages make at runtime.

        Therefore there is a mechanism whereby you can register extra paths
        in this map for a package, and it will be honored.

        Parameters
        ----------
        directory : str
            Absolute or relative path of the directory to be appended to
            this package's ``__path__`` attribute.
        """

        self._module_graph.append_package_path(self.module_name, directory)


class PreFindModulePathAPI:
    """
    Metadata communicating changes made by the current **pre-find module
    path hook** (i.e., hook run immediately _before_ the graph searches for
    the hooked module's file) back to PyInstaller.

    Pre-find module path hooks _must_ define a ``pre_find_module_path()``
    function accepting an instance of this class, whose attributes describe
    the module search to be performed.

    Pre-find module path hooks are typically used to change the absolute
    path from which a module will be subsequently imported and thus frozen
    into the executable. To do so, hooks may overwrite the default
    ``search_dirs`` list of the absolute paths of all directories to be
    searched for that module: e.g.,

        def pre_find_module_path(api):
            api.search_dirs = ['/the/one/true/package/providing/this/module']

    Each pre-find module path hook is run _only_ on the first search for the
    corresponding module.

    Attributes
    ----------
    The following attributes are **mutable** (i.e., modifiable). All changes
    to these attributes will be immediately respected by PyInstaller:

    search_dirs : list
        List of the absolute paths of all directories to be searched for
        this module (in order). Searching will halt at the first directory
        containing this module.

    Attributes (Immutable)
    ----------
    The following attributes are **immutable** (i.e., read-only). For
    safety, any attempts to change these attributes _will_ result in a
    raised exception:

    module_name : str
        Fully-qualified name of this module.
    module_graph : ModuleGraph
        Current module graph. For efficiency, this attribute is technically
        mutable. To preserve graph integrity, this attribute should
        nonetheless _never_ be modified. While read-only ``ModuleGraph``
        methods are safely callable from within pre-find module path hooks,
        methods modifying the graph are _not_. If graph modifications are
        required, consider an alternative type of hook (e.g., pre-import
        module hooks).
    """

    def __init__(
        self,
        module_graph,
        module_name,
        search_dirs,
    ):
        # Mutable attributes.
        self.search_dirs = search_dirs

        # Immutable attributes.
        self._module_graph = module_graph
        self._module_name = module_name

    # Immutable properties. No corresponding setters are defined.
    @property
    def module_graph(self):
        """
        Current module graph.
        """
        return self._module_graph

    @property
    def module_name(self):
        """
        Fully-qualified name of this module.
        """
        return self._module_name


class PostGraphAPI:
    """
    Metadata communicating changes made by the current **post-graph hook**
    (i.e., hook run for a specific module transitively imported by the
    current application _after_ the module graph of all ``import``
    statements performed by this application has been constructed) back to
    PyInstaller.

    Post-graph hooks may optionally define a ``hook()`` function accepting
    an instance of this class, whose attributes describe the current state
    of the module graph and the hooked module's graph node.

    Attributes (Mutable)
    ----------
    The following attributes are **mutable** (i.e., modifiable). All changes
    to these attributes will be immediately respected by PyInstaller:

    module_graph : ModuleGraph
        Current module graph.
    module : Node
        Graph node for the currently hooked module.

    'With great power comes great responsibility.'

    Attributes (Immutable)
    ----------
    The following attributes are **immutable** (i.e., read-only). For
    safety, any attempts to change these attributes _will_ result in a
    raised exception:

    __name__ : str
        Fully-qualified name of this module (e.g., `six.moves.tkinter`).
    __file__ : str
        Absolute path of this module. If this module is:
        * A standard (rather than namespace) package, this is the absolute
          path of the package's ``__init__.py`` file.
        * A namespace (rather than standard) package, this is ``None``
          (namespace packages have no ``__init__.py`` file).
        * A non-package module or C extension, this is the absolute path of
          the corresponding file.
    __path__ : tuple
        Tuple of the absolute paths of all directories comprising this
        package if this module is a package _or_ `None` otherwise. If this
        module is a standard (rather than namespace) package, this tuple
        contains only the absolute path of this package's directory.
    co : code
        Code object compiled from the contents of ``__file__`` (e.g., via
        the ``compile()`` builtin).
    analysis: build_main.Analysis
        The Analysis that loads the hook.

    Attributes (Private)
    ----------
    The following attributes are technically mutable but private, and hence
    should _never_ be externally accessed or modified by hooks. Call the
    corresponding public methods instead:

    _added_datas : list
        List of the ``(name, path)`` 2-tuples or TOC objects of all external
        data files required by the current hook, defaulting to the empty
        list. This is equivalent to the global `datas` hook attribute.
    _added_imports : list
        List of the fully-qualified names of all modules imported by the
        current hook, defaulting to the empty list. This is equivalent to
        the global `hiddenimports` hook attribute.
    _added_binaries : list
        List of the ``(name, path)`` 2-tuples or TOC objects of all external
        C extensions imported by the current hook, defaulting to the empty
        list. This is equivalent to the global `binaries` hook attribute.
    _module_collection_mode : dict
        Dictionary of package/module names and their corresponding
        collection mode strings. This is equivalent to the global
        `module_collection_mode` hook attribute.
    _bindepend_symlink_suppression : set
        A set of paths or path patterns corresponding to shared libraries
        for which binary dependency analysis should not generate symbolic
        links into top-level application directory.
    """

    def __init__(self, module_name, module_graph, analysis):
        # Mutable attributes.
        self.module_graph = module_graph
        self.module = module_graph.find_node(module_name)
        assert self.module is not None  # should not occur

        # Immutable attributes.
        self.___name__ = module_name
        self.___file__ = self.module.path
        self._co = self.module.code
        self._analysis = analysis

        # The package's search locations, if this is a package. The spec
        # carries them verbatim from importlib; fabricating them here would
        # risk divergence from what the analysis actually used.
        self.___path__ = None
        if self.module.spec is not None and self.module.spec.submodule_search_locations is not None:
            # To enforce immutability, convert the search locations into an
            # immutable tuple.
            self.___path__ = tuple(self.module.spec.submodule_search_locations)

        # FIXME: Refactor "_added_datas", "_added_binaries", and
        # "_deleted_imports" into sets. Since order of import is important,
        # "_added_imports" must remain a list.

        # Private attributes.
        self._added_binaries = []
        self._added_datas = []
        self._added_imports = []
        self._deleted_imports = []
        self._module_collection_mode = {}
        self._bindepend_symlink_suppression = set()

    # Immutable properties. No corresponding setters are defined.
    @property
    def __file__(self):
        """
        Absolute path of this module's file.
        """
        return self.___file__

    @property
    def __path__(self):
        """
        Tuple of the absolute paths of all directories comprising this
        package if this module is a package _or_ `None` otherwise.
        """
        return self.___path__

    @property
    def __name__(self):
        """
        Fully-qualified name of this module (e.g., `six.moves.tkinter`).
        """
        return self.___name__

    @property
    def co(self):
        """
        Code object compiled from the contents of ``__file__`` (e.g., via
        the ``compile()`` builtin).
        """
        return self._co

    @property
    def analysis(self):
        """
        build_main.Analysis that calls the hook.
        """
        return self._analysis

    # Obsolete immutable properties provided to preserve backward
    # compatibility.
    @property
    def name(self):
        """
        Fully-qualified name of this module (e.g., `six.moves.tkinter`).

        **This property has been deprecated by the ``__name__`` property.**
        """
        return self.___name__

    @property
    def graph(self):
        """
        Current module graph.

        **This property has been deprecated by the ``module_graph``
        property.**
        """
        return self.module_graph

    @property
    def node(self):
        """
        Graph node for the currently hooked module.

        **This property has been deprecated by the ``module`` property.**
        """
        return self.module

    # TODO: This incorrectly returns the list of the graph nodes of all
    #       modules *TRANSITIVELY* (rather than directly) imported by this
    #       module. Unfortunately, this implies that most uses of this
    #       property are currently broken (e.g.,
    #       "hook-PIL.SpiderImagePlugin.py"). We only require this for the
    #       aforementioned hook, so contemplate alternative approaches.
    @property
    def imports(self):
        """
        List of the graph nodes of all modules directly imported by this
        module.
        """
        return self.module_graph.iter_graph(start=self.module)

    def add_imports(self, *module_names):
        """
        Add all Python modules whose fully-qualified names are in the passed
        list as "hidden imports" upon which the current module depends.

        This is equivalent to appending such names to the hook-specific
        ``hiddenimports`` attribute.
        """
        # Append such names to the current list of all such names.
        self._added_imports.extend(module_names)

    def del_imports(self, *module_names):
        """
        Remove the named fully-qualified modules from the set of imports
        (either hidden or visible) upon which the current module depends.

        This is equivalent to appending such names to the hook-specific
        ``excludedimports`` attribute.
        """
        self._deleted_imports.extend(module_names)

    def add_binaries(self, binaries):
        """
        Add all external dynamic libraries in the passed list of
        ``(src_name, dest_name)`` 2-tuples as dependencies of the current
        module. This is equivalent to adding to the global ``binaries`` hook
        attribute.

        For convenience, the ``binaries`` may also be a list of TOC-style
        3-tuples ``(dest_name, src_name, typecode)``.
        """

        # Detect TOC 3-tuple list by checking the length of the first entry
        if binaries and len(binaries[0]) == 3:
            self._added_binaries.extend(entry[:2] for entry in binaries)
        else:
            # NOTE: `format_binaries_and_datas` changes tuples from input
            # format `(src_name, dest_name)` to output format
            # `(dest_name, src_name)`.
            self._added_binaries.extend(format_binaries_and_datas(binaries))

    def add_datas(self, datas):
        """
        Add all external data files in the passed list of
        ``(src_name, dest_name)`` 2-tuples as dependencies of the current
        module. This is equivalent to adding to the global ``datas`` hook
        attribute.

        For convenience, the ``datas`` may also be a list of TOC-style
        3-tuples ``(dest_name, src_name, typecode)``.
        """

        # Detect TOC 3-tuple list by checking the length of the first entry
        if datas and len(datas[0]) == 3:
            self._added_datas.extend(entry[:2] for entry in datas)
        else:
            # NOTE: `format_binaries_and_datas` changes tuples from input
            # format `(src_name, dest_name)` to output format
            # `(dest_name, src_name)`.
            self._added_datas.extend(format_binaries_and_datas(datas))

    def set_module_collection_mode(self, name, mode):
        """"
        Set the package/module collection mode for the specified module
        name. If ``name`` is `None`, the hooked module/package name is used.
        ``mode`` can be one of valid mode strings ('pyz', 'pyc', 'py',
        'pyz+py', 'py+pyz') or `None`, which clears the setting for the
        module/package - but only within this hook's context!
        """
        if name is None:
            name = self.__name__
        if mode is None:
            self._module_collection_mode.pop(name)
        else:
            self._module_collection_mode[name] = mode

    def add_bindepend_symlink_suppression_pattern(self, pattern):
        """
        Add the given path or path pattern to the set of patterns that
        prevent binary dependency analysis from creating a symbolic link to
        the top-level application directory.
        """
        self._bindepend_symlink_suppression.add(pattern)


def _module_collection_mode_sanitizer(value):
    if isinstance(value, dict):
        # Hook set a dictionary; use it as-is
        return value
    elif isinstance(value, str):
        # Hook set a mode string; convert to a dictionary and assign the
        # string to `None` (= the hooked module).
        return {None: value}

    raise ValueError(f"Invalid module collection mode setting value: {value!r}")


def _bindepend_symlink_suppression_sanitizer(value):
    if isinstance(value, (list, set)):
        # Hook set a list or a set; use it as-is
        return set(value)
    elif isinstance(value, str):
        # Hook set a string; create a set with single element.
        return set([value])

    raise ValueError(f"Invalid value for bindepend_symlink_suppression: {value!r}")


# Dictionary mapping the names of magic attributes required by the
# "ModuleHook" class to 2-tuples "(default_type, sanitizer_func)", where:
#
# * "default_type" is the type to which that attribute will be initialized
#   when that hook is lazily loaded.
# * "sanitizer_func" is the callable sanitizing the original value of that
#   attribute defined by that hook into a safer value consumable by
#   "ModuleHook" callers if any or "None" if the original value requires no
#   sanitization.
#
# To avoid subtleties in the ModuleHook.__getattr__() method, this
# dictionary is declared as a module rather than a class attribute. If
# declared as a class attribute and then undefined (...for whatever reason),
# attempting to access this attribute from that method would produce
# infinite recursion.
_MAGIC_MODULE_HOOK_ATTRS = {
    # Collections in which order is insignificant. This includes:
    #
    # * "datas", sanitized from hook-style 2-tuple lists defined by hooks
    #   into TOC-style 2-tuple sets consumable by "ModuleHook" callers.
    # * "binaries", sanitized in the same way.
    'datas': (set, format_binaries_and_datas),
    'binaries': (set, format_binaries_and_datas),
    'excludedimports': (set, None),

    # Collections in which order is significant. This includes:
    #
    # * "hiddenimports", as order of importation is significant. On module
    #   importation, hook scripts are loaded and hook functions declared by
    #   these scripts are called. As these scripts and functions can have
    #   side effects dependent on module importation order, module
    #   importation itself can have side effects dependent on this order!
    'hiddenimports': (list, None),

    # Flags
    'warn_on_missing_hiddenimports': (lambda: True, bool),

    # Package/module collection mode dictionary.
    'module_collection_mode': (dict, _module_collection_mode_sanitizer),

    # Path patterns for suppression of symbolic links created by binary
    # dependency analysis.
    'bindepend_symlink_suppression': (set, _bindepend_symlink_suppression_sanitizer),
}


class ModuleHook:
    """
    Cached object encapsulating a lazy loadable hook script.

    This object exposes public attributes (e.g., `datas`) of the underlying
    hook script as attributes of the same name of this object. On the first
    access of any such attribute, this hook script is lazily loaded into an
    in-memory private module reused on subsequent accesses. These dynamic
    attributes are referred to as "magic." All other static attributes of
    this object (e.g., `hook_module_name`) are referred to as "non-magic."

    Attributes (Magic)
    ----------
    datas : set
        Set of `TOC`-style 2-tuples `(target_file, source_file)` for all
        external non-executable files required by the module being hooked,
        converted from the `datas` list of hook-style 2-tuples
        `(source_dir_or_glob, target_dir)` defined by this hook script.
    binaries : set
        Set of `TOC`-style 2-tuples `(target_file, source_file)` for all
        external executable files required by the module being hooked,
        converted from the `binaries` list of hook-style 2-tuples
        `(source_dir_or_glob, target_dir)` defined by this hook script.
    excludedimports : set
        Set of the fully-qualified names of all modules imported by the
        module being hooked to be ignored rather than imported from that
        module, converted from the `excludedimports` list defined by this
        hook script. These modules will only be "locally" rather than
        "globally" ignored. These modules will remain importable from all
        modules other than the module being hooked.
    hiddenimports : set
        Set of the fully-qualified names of all modules imported by the
        module being hooked that are _not_ automatically detectable by
        PyInstaller (usually due to being dynamically imported in that
        module), converted from the `hiddenimports` list defined by this
        hook script.
    warn_on_missing_hiddenimports : bool
        Boolean flag indicating whether missing hidden imports from the hook
        should generate warnings or not. This behavior is enabled by default,
        but individual hooks can opt out of it.
    module_collection_mode : dict
        A dictionary of package/module names and their corresponding
        collection mode strings ('pyz', 'pyc', 'py', 'pyz+py', 'py+pyz').
    bindepend_symlink_suppression : set
        A set of paths or path patterns corresponding to shared libraries
        for which binary dependency analysis should not create symbolic
        links into top-level application directory.

    Attributes (Non-magic)
    ----------
    module_graph : ModuleGraph
        Current module graph.
    module_name : str
        Name of the module hooked by this hook script.
    hook_filename : str
        Absolute or relative path of this hook script.
    hook_module_name : str
        Name of the in-memory module of this hook script's interpreted
        contents.
    _hook_module : module
        In-memory module of this hook script's interpreted contents, lazily
        loaded on the first call to the `_load_hook_module()` method _or_
        `None` if this method has yet to be accessed.
    _default_priority : int
        Default (location-based) priority for this hook.
    priority : int
        Actual priority for this hook. Might be different from
        `_default_priority` if hook file specifies the hook priority
        override.
    """

    #-- Magic --

    def __init__(self, module_graph, module_name, hook_filename, hook_module_name_prefix, default_priority):
        """
        Initialize this metadata.

        Parameters
        ----------
        module_graph : ModuleGraph
            Current module graph (as a weak reference; see
            ``ModuleHookCache.__init__()``).
        module_name : str
            Name of the module hooked by this hook script.
        hook_filename : str
            Absolute or relative path of this hook script.
        hook_module_name_prefix : str
            String prefixing the name of the in-memory module for this hook
            script. To avoid namespace clashes with similar modules created
            by other `ModuleHook` objects in other `ModuleHookCache`
            containers, this string _must_ be unique to the
            `ModuleHookCache` container containing this `ModuleHook` object.
            If this string is non-unique, an existing in-memory module will
            be erroneously reused when lazily loading this hook script, thus
            erroneously re-sanitizing previously sanitized hook script
            attributes (e.g., `datas`) with the `format_binaries_and_datas()`
            helper.
        default_priority : int
            Default, location-based priority for this hook. Used to select
            active hook when multiple hooks are defined for the same module.
        """
        # Note that the passed module graph is already a weak reference,
        # avoiding circular reference issues. See ModuleHookCache.__init__().
        assert isinstance(module_graph, weakref.ProxyTypes)
        self.module_graph = module_graph
        self.module_name = module_name
        self.hook_filename = hook_filename

        # Default priority; used as fall-back for dynamic `hook_priority`
        # attribute.
        self._default_priority = default_priority

        # Name of the in-memory module fabricated to refer to this hook
        # script.
        self.hook_module_name = hook_module_name_prefix + self.module_name.replace('.', '_')

        # Attributes subsequently defined by the _load_hook_module() method.
        self._loaded = False
        self._has_hook_function = False
        self._hook_module = None

    def __getattr__(self, attr_name):
        """
        Get the magic attribute with the passed name (e.g., `datas`) from
        this lazily loaded hook script if any _or_ raise `AttributeError`
        otherwise.

        This special method is called only for attributes _not_ already
        defined by this object. This includes undefined attributes and the
        first attempt to access magic attributes.

        This special method is _not_ called for subsequent attempts to
        access magic attributes. The first attempt to access magic
        attributes defines corresponding instance variables accessible via
        the `self.__dict__` instance dictionary (e.g., as `self.datas`)
        without calling this method. This approach also allows magic
        attributes to be deleted from this object _without_ defining the
        `__delattr__()` special method.

        See Also
        ----------
        Class docstring for supported magic attributes.
        """

        if attr_name == 'priority':
            # If attribute is part of hook metadata, read metadata from hook
            # script and return the attribute value.
            self._load_hook_metadata()
            return getattr(self, attr_name)
        if attr_name in _MAGIC_MODULE_HOOK_ATTRS and not self._loaded:
            # If attribute is hook's magic attribute, load and run the hook
            # script, and return the attribute value.
            self._load_hook_module()
            return getattr(self, attr_name)
        else:
            # This is an undefined attribute. Raise an exception.
            raise AttributeError(attr_name)

    def __setattr__(self, attr_name, attr_value):
        """
        Set the attribute with the passed name to the passed value.

        If this is a magic attribute, this hook script will be lazily loaded
        before setting this attribute. Unlike `__getattr__()`, this special
        method is called to set _any_ attribute -- including magic,
        non-magic, and undefined attributes.

        See Also
        ----------
        Class docstring for supported magic attributes.
        """

        # If this is a magic attribute, initialize this attribute by lazy
        # loading this hook script before overwriting this attribute.
        if attr_name in _MAGIC_MODULE_HOOK_ATTRS:
            self._load_hook_module()

        # Set this attribute to the passed value. To avoid recursion, the
        # superclass method rather than setattr() is called.
        return super().__setattr__(attr_name, attr_value)

    #-- Loading --

    def _load_hook_metadata(self):
        """
        Load hook metadata from its source file.
        """
        self.priority = self._default_priority

        # Priority override pattern: `# $PyInstaller-Hook-Priority: <value>`
        priority_pattern = re.compile(r"^\s*#\s*\$PyInstaller-Hook-Priority:\s*(?P<value>[\S]+)")

        with open(self.hook_filename, "r", encoding="utf-8") as f:
            for line in f:
                # Attempt to match and parse hook priority directive
                m = priority_pattern.match(line)
                if m is not None:
                    try:
                        self.priority = int(m.group('value'))
                    except Exception:
                        logger.warning(
                            "Failed to parse hook priority value string: %r!", m.group('value'), exc_info=True
                        )
                    # Currently, this is our only line of interest, so we can
                    # stop the search here.
                    return

    def _load_hook_module(self, keep_module_ref=False):
        """
        Lazily load this hook script into an in-memory private module.

        This method (and, indeed, this class) preserves all attributes and
        functions defined by this hook script as is, ensuring sane behaviour
        in hook functions _not_ expecting unplanned external modification.
        Instead, this method copies public attributes defined by this hook
        script (e.g., `binaries`) into private attributes of this object,
        which the special `__getattr__()` and `__setattr__()` methods safely
        expose to external callers. For public attributes _not_ defined by
        this hook script, the corresponding private attributes will be
        assigned sane defaults. For some public attributes defined by this
        hook script, the corresponding private attributes will be
        transformed into objects more readily and safely consumed elsewhere
        by external callers.

        See Also
        ----------
        Class docstring for supported attributes.
        """

        # If this hook script module has already been loaded, noop.
        if self._loaded and (self._hook_module is not None or not keep_module_ref):
            return

        # Load and execute the hook script. Even if mechanisms from the
        # import machinery are used, this does not import the hook as the
        # module.
        hook_path, hook_basename = os.path.split(self.hook_filename)
        logger.info('Processing standard module hook %r from %r', hook_basename, hook_path)
        try:
            self._hook_module = importlib_load_source(self.hook_module_name, self.hook_filename)
        except ImportError:
            logger.debug("Hook failed with:", exc_info=True)
            raise ImportErrorWhenRunningHook(self.hook_module_name, self.hook_filename)

        # Mark as loaded
        self._loaded = True

        # Check if module has hook() function.
        self._has_hook_function = hasattr(self._hook_module, 'hook')

        # Copy hook script attributes into magic attributes exposed as
        # instance variables of the current "ModuleHook" instance.
        for attr_name, (default_type, sanitizer_func) in _MAGIC_MODULE_HOOK_ATTRS.items():
            # Unsanitized value of this attribute.
            attr_value = getattr(self._hook_module, attr_name, None)

            # If this attribute is undefined, expose a sane default instead.
            if attr_value is None:
                attr_value = default_type()
            # Else if this attribute requires sanitization, do so.
            elif sanitizer_func is not None:
                attr_value = sanitizer_func(attr_value)
            # Else, expose the unsanitized value of this attribute.

            # Expose this attribute as an instance variable of the same name.
            setattr(self, attr_name, attr_value)

        # If module_collection_mode has an entry with None key, reassign it
        # to the hooked module's name.
        setattr(
            self, 'module_collection_mode', {
                key if key is not None else self.module_name: value
                for key, value in getattr(self, 'module_collection_mode').items()
            }
        )

        # Release the module if we do not need the reference. This is the
        # case when the hook is loaded during the analysis rather than as
        # part of the post-graph operations.
        if not keep_module_ref:
            self._hook_module = None

    #-- Hooks --

    def post_graph(self, analysis):
        """
        Call the **post-graph hook** (i.e., `hook()` function) defined by
        this hook script, if any.

        Parameters
        ----------
        analysis: build_main.Analysis
            Analysis that calls the hook

        This method is intended to be called _after_ the module graph for
        this application is constructed.
        """

        # Lazily load this hook script into an in-memory module.
        # The script might have been loaded before during the analysis; in
        # that case, it needs to be reloaded only if it provides a hook()
        # function.
        if not self._loaded or self._has_hook_function:
            # Keep module reference when loading the hook, so we can call
            # its hook function!
            self._load_hook_module(keep_module_ref=True)

            # Call this hook script's hook() function, which modifies
            # attributes accessed by subsequent methods and hence must be
            # called first.
            self._process_hook_func(analysis)

        # Order is insignificant here.
        self._process_hidden_imports()

    def _process_hook_func(self, analysis):
        """
        Call this hook's `hook()` function if defined.

        Parameters
        ----------
        analysis: build_main.Analysis
            Analysis that calls the hook
        """

        # If this hook script defines no hook() function, noop.
        if not hasattr(self._hook_module, 'hook'):
            return

        # Call this hook() function.
        hook_api = PostGraphAPI(module_name=self.module_name, module_graph=self.module_graph, analysis=analysis)
        try:
            self._hook_module.hook(hook_api)
        except ImportError:
            logger.debug("Hook failed with:", exc_info=True)
            raise ImportErrorWhenRunningHook(self.hook_module_name, self.hook_filename)

        # Update all magic attributes modified by the prior call.
        self.datas.update(set(hook_api._added_datas))
        self.binaries.update(set(hook_api._added_binaries))
        self.hiddenimports.extend(hook_api._added_imports)
        self.module_collection_mode.update(hook_api._module_collection_mode)
        self.bindepend_symlink_suppression.update(hook_api._bindepend_symlink_suppression)

        # FIXME: `hook_api._deleted_imports` should be appended to
        # `self.excludedimports` and used to suppress module import during
        # the graph construction rather than handled here. However, for that
        # to work, the `hook()` function needs to be ran during the graph
        # construction instead of in post-processing (and this in turn
        # requires additional code refactoring in order to be able to pass
        # `analysis` to `PostGraphAPI` object at that point). So once the
        # hook refactor (upstream issues #1900-#1902) is complete, remove
        # the code block below.
        for deleted_module_name in hook_api._deleted_imports:
            # Remove the graph link between the hooked module and item. This
            # removes the 'item' node from the graph if no other links go to
            # it (no other modules import it).
            self.module_graph.remove_reference(hook_api.module, deleted_module_name)

    def _process_hidden_imports(self):
        """
        Add all imports listed in this hook script's `hiddenimports`
        attribute to the module graph as if directly imported by this hooked
        module.

        These imports are typically _not_ implicitly detectable by
        PyInstaller and hence must be explicitly defined by hook scripts.
        """

        # For each hidden import required by the module being hooked...
        for import_module_name in self.hiddenimports:
            try:
                # Graph node for this module, if it made it into the graph.
                caller = self.module_graph.find_node(self.module_name)

                # Manually import this hidden import from this module.
                self.module_graph.import_hook(import_module_name, caller)
            # If this hidden import is unimportable, print a non-fatal
            # warning. Hidden imports often become desynchronized from
            # upstream packages and hence are only "soft" recommendations.
            except ImportError:
                if self.warn_on_missing_hiddenimports:
                    logger.warning('Hidden import "%s" not found!', import_module_name)


class AdditionalFilesCache:
    """
    Cache for storing what binaries and datas were pushed by what modules
    when import hooks were processed.
    """

    def __init__(self):
        self._binaries = {}
        self._datas = {}

    def add(self, modname, binaries, datas):

        self._binaries.setdefault(modname, [])
        self._binaries[modname].extend(binaries or [])
        self._datas.setdefault(modname, [])
        self._datas[modname].extend(datas or [])

    def __contains__(self, name):
        return name in self._binaries or name in self._datas

    def binaries(self, modname):
        """
        Return list of binaries for given module name.
        """
        return self._binaries.get(modname, [])

    def datas(self, modname):
        """
        Return list of datas for given module name.
        """
        return self._datas.get(modname, [])
