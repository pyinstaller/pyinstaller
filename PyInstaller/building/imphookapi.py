#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Classes facilitating communication between PyInstaller and import hooks.

PyInstaller passes instances of classes defined by this module to corresponding
functions defined by external import hooks, which commonly modify the contents
of these instances before returning. PyInstaller then detects and converts these
modifications into appropriate operations on the current `PyiModuleGraph`
instance, thus modifying which modules will be frozen into the executable.
"""

from .datastruct import TOC

class PreSafeImportModuleAPI(object):
    """
    Metadata communicating changes made by the current **pre-safe import module
    hook** (i.e., hook run immediately _before_ a call to
    `ModuleGraph._safe_import_module()` recursively adding the hooked module,
    package, or C extension and all transitive imports thereof to the module
    graph) back to PyInstaller.

    Pre-safe import module hooks _must_ define a `pre_safe_import_module()`
    function accepting an instance of this class, whose attributes describe the
    subsequent `ModuleGraph._safe_import_module()` call creating the hooked
    module's graph node.

    Each pre-safe import module hook is run _only_ on the first attempt to
    create the hooked module's graph node and then subsequently ignored. If this
    hook successfully creates that graph node, the subsequent
    `ModuleGraph._safe_import_module()` call will observe this fact and silently
    return without attempting to recreate that graph node.

    Pre-safe import module hooks are typically used to create graph nodes for
    **runtime modules** (i.e., modules dynamically defined at runtime). Most
    modules are physically defined in external `.py`-suffixed scripts. Some
    modules, however, are dynamically defined at runtime (e.g., `six.moves`,
    dynamically defined by the physically defined `six.py` module). However,
    `ModuleGraph` only parses `import` statements residing in external scripts.
    `ModuleGraph` is _not_ a full-fledged, Turing-complete Python interpreter
    and hence has no means of parsing `import` statements performed by runtime
    modules existing only in-memory.

    Attributes (Mutable)
    ----------
    The following attributes are **mutable** (i.e., modifiable). All changes to
    these attributes will be respected by PyInstaller, typically immediately
    after the current hook returns:

    module_graph : PyiModuleGraph
        Current module graph.
    module_basename : str
        Unqualified name of the module to be imported (e.g., `text`).
    module_name : str
        Fully-qualified name of this module (e.g., `email.mime.text`).
    parent_package : Package
        Graph node for the package providing this module _or_ `None` if this
        module is a top-level module.

    "With great power comes great responsibility."
    """

    def __init__(
        self,
        module_graph,
        module_basename,
        module_name,
        parent_package,
    ):
        self.module_graph = module_graph
        self.module_basename = module_basename
        self.module_name = module_name
        self.parent_package = parent_package


class PreFindModulePathAPI(object):
    """
    Metadata communicating changes made by the current **pre-find module
    path hook** (i.e., hook run immediately _before_ a call to
    `ModuleGraph._find_module_path()` finding the hooked module's absolute
    path) back to PyInstaller.

    Pre-find module path hooks _must_ define a `pre_find_module_path()`
    function accepting an instance of this class, whose attributes describe the
    subsequent `ModuleGraph._find_module_path()` call to be performed.

    Pre-find module path hooks are typically used to change the absolute
    path from which a module will be subsequently imported and thus frozen into
    the executable. To do so, hooks may overwrite the default `search_dirs` list
    of the absolute paths of all directories to be searched for that module:
    e.g.,

        def pre_find_module_path(api):
            api.search_dirs = ['/the/one/true/package/providing/this/module']

    Each pre-find module path hook is run _only_ on the first call to
    `ModuleGraph._find_module_path()` for the corresponding module.

    Attributes
    ----------
    The following attributes are **mutable** (i.e., modifiable). All changes to
    these attributes will be immediately respected by PyInstaller:

    search_dirs : list
        List of the absolute paths of all directories to be searched for this
        module (in order). Searching will halt at the first directory containing
        this module.

    Attributes (Immutable)
    ----------
    The following attributes are **immutable** (i.e., read-only). For safety,
    any attempts to change these attributes _will_ result in a raised exception:

    module_name : str
        Fully-qualified name of this module.
    module_graph : PyiModuleGraph
        Current module graph. For efficiency, this attribute is technically
        mutable. To preserve graph integrity, this attribute should nonetheless
        _never_ be modified. While read-only `PyiModuleGraph` methods (e.g.,
        `findNode()`) are safely callable from within pre-find module path
        hooks, methods modifying the graph are _not_. If graph modifications are
        required, consider an alternative type of hook (e.g., pre-import module
        hooks).
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
        Current module graph
        """
        return self._module_graph

    @property
    def module_name(self):
        """
        Fully-qualified name of this module.
        """
        return self._module_name


class PostGraphAPI(object):
    """
    Metadata communicating changes made by the current **post-graph hook**
    (i.e., hook run for a specific module transitively imported by the current
    application _after_ the module graph of all `import` statements performed by
    this application has been constructed) back to PyInstaller.

    Post-graph hooks may optionally define a `post_graph()` function accepting
    an instance of this class, whose attributes describe the current state of
    the module graph and the hooked module's graph node.

    Attributes (Mutable)
    ----------
    The following attributes are **mutable** (i.e., modifiable). All changes to
    these attributes will be immediately respected by PyInstaller:

    module_graph : PyiModuleGraph
        Current module graph.
    module : Node
        Graph node for the currently hooked module.

    "With great power comes great responsibility."

    Attributes (Immutable)
    ----------
    The following attributes are **immutable** (i.e., read-only). For safety,
    any attempts to change these attributes _will_ result in a raised exception:

    __name__ : str
        Fully-qualified name of this module (e.g., `six.moves.tkinter`).
    __file__ : str
        Absolute path of this module. If this module is:
        * A standard (rather than namespace) package, this is the absolute path
          of this package's directory.
        * A namespace (rather than standard) package, this is the abstract
          placeholder `-`. (Don't ask. Don't tell.)
        * A non-package module or C extension, this is the absolute path of the
          corresponding file.
    __path__ : list
        List of the absolute paths of all directories comprising this package
        if this module is a package _or_ `None` otherwise. If this module is a
        standard (rather than namespace) package, this list contains only the
        absolute path of this package's directory.
    co : code
        Code object compiled from the contents of `__file__` (e.g., via the
        `compile()` builtin).

    Attributes (Private)
    ----------
    The following attributes are technically mutable but private, and hence
    should _never_ be externally accessed or modified by hooks. Call the
    corresponding public methods instead:

    _added_datas : list
        List of the `(name, path)` 2-tuples or TOC objects of all
        external data files required by the current hook, defaulting to the
        empty list. This is equivalent to the global `datas` hook attribute.
    _added_imports : list
        List of the fully-qualified names of all modules imported by the current
        hook, defaulting to the empty list. This is equivalent to the global
        `hiddenimports` hook attribute.
    _added_binaries : list
        List of the `(name, path)` 2-tuples or TOC objects of all
        external C extensions imported by the current hook, defaulting to the
        empty list. This is equivalent to the global
        `binaries` hook attribute.
    """

    def __init__(self, module_name, module_graph):
        # Mutable attributes.
        self.module_graph = module_graph
        self.module = module_graph.findNode(module_name)
        assert self.module is not None  # should not occur

        # Immutable attributes.
        self.___name__ = module_name
        self.___file__ = self.module.filename
        self._co = self.module.code

        # To enforce immutability, convert this module's package path if any
        # into an immutable tuple.
        self.___path__ = tuple(self.module.packagepath) \
            if self.module.packagepath is not None else None

        # Private attributes.
        self._added_binaries = []
        self._added_datas = []
        self._added_imports = []
        self._deleted_imports = []

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
        List of the absolute paths of all directories comprising this package
        if this module is a package _or_ `None` otherwise. If this module is a
        standard (rather than namespace) package, this list contains only the
        absolute path of this package's directory.
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
        Code object compiled from the contents of `__file__` (e.g., via the
        `compile()` builtin).
        """
        return self._co

    # Obsolete immutable properties provided to preserve backward compatibility.
    @property
    def name(self):
        """
        Fully-qualified name of this module (e.g., `six.moves.tkinter`).

        **This property has been deprecated by the `__name__` property.**
        """
        return self.___name__

    @property
    def graph(self):
        """
        Current module graph.

        **This property has been deprecated by the `module_graph` property.**
        """
        return self.module_graph

    @property
    def node(self):
        """
        Graph node for the currently hooked module.

        **This property has been deprecated by the `module` property.**
        """
        return self.module

    # TODO: This incorrectly returns the list of the graph nodes of all modules
    # *TRANSITIVELY* (rather than directly) imported by this module.
    # Unfortunately, this implies that most uses of this property are currently
    # broken (e.g., "hook-PIL.SpiderImagePlugin.py"). We only require this for
    # the aforementioned hook, so contemplate alternative approaches.
    @property
    def imports(self):
        """
        List of the graph nodes of all modules directly imported by this module.
        """
        return self.module_graph.flatten(start=self.module)

    def add_imports(self, module_names):
        """
        Add all Python modules whose fully-qualified names are in the passed
        list as "hidden imports" upon which the current module depends.

        This is equivalent to appending such names to the hook-specific
        `hiddenimports` attribute. For convenience, the passed argument may be
        either a single module name _or_ list of module names.
        """
        # If the passed object is a string, convert that to a list containing
        # only this string for convenience.
        if isinstance(module_names, str):
            module_names = [module_names]

        # Append such names to the current list of all such names.
        self._added_imports.extend(module_names)

    def del_imports(self, module_names):
        """
        Remove all Python modules whose `.`-delimited names are in the passed
        list from the set of imports (either hidden or visible) upon which the
        current module depends.

        The passed argument may be either a list of module names _or_ a single
        module name.
        """
        # If the passed object is a string, convert that to a list containing
        # only this string for convenience.
        if isinstance(module_names, str):
            module_names = [module_names]
        self._deleted_imports.extend(module_names)

    def add_binaries(self, list_of_tuples):
        """
        Add all external dynamic libraries in the passed list of
        `(name, path)` 2-tuples as dependencies of the current module.
        This is equivalent to adding to the global `binaries` hook
        attribute.

        For convenience, the `list_of_tuples` may also be a single TOC
        or TREE instance.
        """
        if isinstance(list_of_tuples, TOC):
            self._added_binaries.extend(i[:2] for i in list_of_tuples)
        else:
            self._added_binaries.extend(list_of_tuples)

    def add_datas(self, list_of_tuples):
        """
        Add all external data files in the passed list of `(name,
        path)` 2-tuples as dependencies of the current module. This is
        equivalent to adding to the global `datas` hook attribute.

        For convenience, the `list_of_tuples` may also be a single TOC
        or TREE instance.
        """
        if isinstance(list_of_tuples, TOC):
            self._added_datas.extend(i[:2] for i in list_of_tuples)
        else:
            self._added_datas.extend(list_of_tuples)
