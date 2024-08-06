#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
PEP-302 and PEP-451 importers for frozen applications.
"""

# **NOTE** This module is used during bootstrap.
# Import *ONLY* builtin modules or modules that are collected into the base_library.zip archive.
# List of built-in modules: sys.builtin_module_names
# List of modules collected into base_library.zip: PyInstaller.compat.PY3_BASE_MODULES

import sys
import os
import io

import _frozen_importlib
import _thread

import pyimod01_archive

if sys.flags.verbose and sys.stderr:

    def trace(msg, *a):
        sys.stderr.write(msg % a)
        sys.stderr.write("\n")
else:

    def trace(msg, *a):
        pass


def _decode_source(source_bytes):
    """
    Decode bytes representing source code and return the string. Universal newline support is used in the decoding.
    Based on CPython's implementation of the same functionality:
    https://github.com/python/cpython/blob/3.9/Lib/importlib/_bootstrap_external.py#L679-L688
    """
    # Local import to avoid including `tokenize` and its dependencies in `base_library.zip`
    from tokenize import detect_encoding
    source_bytes_readline = io.BytesIO(source_bytes).readline
    encoding = detect_encoding(source_bytes_readline)
    newline_decoder = io.IncrementalNewlineDecoder(decoder=None, translate=True)
    return newline_decoder.decode(source_bytes.decode(encoding[0]))


# Global instance of PYZ archive reader. Initialized by install().
pyz_archive = None

# Some runtime hooks might need to traverse available frozen package/module hierarchy to simulate filesystem.
# Such traversals can be efficiently implemented using a prefix tree (trie), whose computation we defer until first
# access.
_pyz_tree_lock = _thread.RLock()
_pyz_tree = None


def get_pyz_toc_tree():
    global _pyz_tree

    with _pyz_tree_lock:
        if _pyz_tree is None:
            _pyz_tree = _build_pyz_prefix_tree(pyz_archive)
        return _pyz_tree


# Fully resolve sys._MEIPASS, so we can compare fully-resolved paths to it.
_RESOLVED_TOP_LEVEL_DIRECTORY = os.path.realpath(sys._MEIPASS)

# If we are running as macOS .app bundle, compute the alternative top-level directory path as well.
_is_macos_app_bundle = False
if sys.platform == 'darwin' and _RESOLVED_TOP_LEVEL_DIRECTORY.endswith("Contents/Frameworks"):
    _is_macos_app_bundle = True
    _ALTERNATIVE_TOP_LEVEL_DIRECTORY = os.path.join(
        os.path.dirname(_RESOLVED_TOP_LEVEL_DIRECTORY),
        'Resources',
    )


# Helper for computing PYZ prefix tree
def _build_pyz_prefix_tree(pyz_archive):
    tree = dict()
    for entry_name, entry_data in pyz_archive.toc.items():
        name_components = entry_name.split('.')
        typecode = entry_data[0]
        current = tree
        if typecode in {pyimod01_archive.PYZ_ITEM_PKG, pyimod01_archive.PYZ_ITEM_NSPKG}:
            # Package; create new dictionary node for its modules
            for name_component in name_components:
                current = current.setdefault(name_component, {})
        else:
            # Module; create the leaf node (empty string)
            for name_component in name_components[:-1]:
                current = current.setdefault(name_component, {})
            current[name_components[-1]] = ''
    return tree


class PyiFrozenImporter:
    """
    PyInstaller's frozen module importer (finder + loader) for specific search path.

    Per-path instances allow us to properly translate the given module name ("fullname") into full PYZ entry name.
    For example, with search path being `sys._MEIPASS`, the module "mypackage.mod" would translate to "mypackage.mod"
    in the PYZ archive. However, if search path was `sys._MEIPASS/myotherpackage/_vendored` (for example, if
    `myotherpacakge` added this path to `sys.path`), then "mypackage.mod" would need to translate to
    "myotherpackage._vendored.mypackage.mod" in the PYZ archive.
    """
    def __repr__(self):
        return f"{self.__class__.__name__}({self._path})"

    @classmethod
    def path_hook(cls, path):
        trace(f"PyInstaller: running path finder hook for path: {path!r}")
        try:
            finder = cls(path)
            trace("PyInstaller: hook succeeded")
            return finder
        except Exception as e:
            trace(f"PyInstaller: hook failed: {e}")
            raise

    @staticmethod
    def _compute_relative_path(path, top_level):
        try:
            relative_path = os.path.relpath(path, top_level)
        except ValueError as e:
            raise ImportError("Path outside of top-level application directory") from e

        if relative_path.startswith('..'):
            raise ImportError("Path outside of top-level application directory")

        return relative_path

    def __init__(self, path):
        self._path = path  # Store original path, as given.
        self._pyz_archive = pyz_archive

        # Resolve path for comparison
        resolved_path = os.path.realpath(path)

        # Compare resolved path to resolved top-level application directory.
        try:
            relative_path = self._compute_relative_path(resolved_path, _RESOLVED_TOP_LEVEL_DIRECTORY)
        except Exception:
            if _is_macos_app_bundle:
                relative_path = self._compute_relative_path(resolved_path, _ALTERNATIVE_TOP_LEVEL_DIRECTORY)
            else:
                raise

        if relative_path == '.':
            self._pyz_entry_prefix = ''
        else:
            self._pyz_entry_prefix = '.'.join(relative_path.split(os.path.sep))

    def _compute_pyz_entry_name(self, fullname):
        """
        Convert module fullname into PYZ entry name, subject to the prefix implied by this finder's search path.
        """
        tail_module = fullname.rpartition('.')[2]

        if self._pyz_entry_prefix:
            return self._pyz_entry_prefix + "." + tail_module
        else:
            return tail_module

    @property
    def fallback_finder(self):
        """
        Opportunistically create a *fallback finder* using `sys.path_hooks` entries that are located *after* our hook.
        The main goal of this exercise is to obtain an instance of python's FileFinder, but in theory any other hook
        that comes after ours is eligible to be a fallback.

        Having this fallback allows our finder to "cooperate" with python's FileFinder, as if the two were a single
        finder, which allows us to work around the python's PathFinder permitting only one finder instance per path
        without subclassing FileFinder.
        """
        if hasattr(self, '_fallback_finder'):
            return self._fallback_finder

        # Try to instantiate fallback finder
        our_hook_found = False

        self._fallback_finder = None
        for idx, hook in enumerate(sys.path_hooks):
            if hook == self.path_hook:
                our_hook_found = True
                continue  # Our hook

            if not our_hook_found:
                continue  # Skip hooks before our hook

            try:
                self._fallback_finder = hook(self._path)
                break
            except ImportError:
                pass

        return self._fallback_finder

    def _find_fallback_spec(self, fullname, target):
        """
        Attempt to find the spec using fallback finder, which is opportunistically created here. Typically, this would
        be python's FileFinder, which can discover specs for on-filesystem modules, such as extension modules and
        modules that are collected only as source .py files.

        Having this fallback allows our finder to "cooperate" with python's FileFinder, as if the two were a single
        finder, which allows us to work around the python's PathFinder permitting only one finder instance per path
        without subclassing FileFinder.
        """
        if not hasattr(self, '_fallback_finder'):
            self._fallback_finder = self._get_fallback_finder()

        if self._fallback_finder is None:
            return None

        return self._fallback_finder.find_spec(fullname, target)

    #-- Core PEP451 finder functionality, modeled after importlib.abc.PathEntryFinder
    # https://docs.python.org/3/library/importlib.html#importlib.abc.PathEntryFinder
    def invalidate_caches(self):
        """
        A method which, when called, should invalidate any internal cache used by the finder. Used by
        importlib.invalidate_caches() when invalidating the caches of all finders on sys.meta_path.

        https://docs.python.org/3/library/importlib.html#importlib.abc.MetaPathFinder.invalidate_caches
        """
        # We do not use any caches, but if we have created a fallback finder, propagate the function call.
        # NOTE: use getattr() with _fallback_finder attribute, in order to avoid unnecessary creation of the
        # fallback finder in case when it does not exist yet.
        fallback_finder = getattr(self, '_fallback_finder', None)
        if fallback_finder is not None:
            if hasattr(fallback_finder, 'invalidate_caches'):
                fallback_finder.invalidate_caches()

    def find_spec(self, fullname, target=None):
        """
        A method for finding a spec for the specified module. The finder will search for the module only within the
        path entry to which it is assigned. If a spec cannot be found, None is returned. When passed in, target is a
        module object that the finder may use to make a more educated guess about what spec to return.

        https://docs.python.org/3/library/importlib.html#importlib.abc.PathEntryFinder.find_spec
        """
        trace(f"{self}: find_spec: called with fullname={fullname!r}, target={fullname!r}")

        # Convert fullname to PYZ entry name.
        pyz_entry_name = self._compute_pyz_entry_name(fullname)

        # Try looking up the entry in the PYZ archive
        entry_data = self._pyz_archive.toc.get(pyz_entry_name)
        if entry_data is None:
            # Entry not found - try using fallback finder (for example, python's own FileFinder) to resolve on-disk
            # resources, such as extension modules and modules that are collected only as source .py files.
            trace(f"{self}: find_spec: {fullname!r} not found in PYZ...")

            if self.fallback_finder is not None:
                trace(f"{self}: find_spec: attempting resolve using fallback finder {self.fallback_finder!r}.")
                fallback_spec = self.fallback_finder.find_spec(fullname, target)
                trace(f"{self}: find_spec: fallback finder returned spec: {fallback_spec!r}.")
                return fallback_spec
            else:
                trace(f"{self}: find_spec: fallback finder is not available.")

            return None

        # Entry found
        typecode = entry_data[0]
        trace(f"{self}: find_spec: found {fullname!r} in PYZ as {pyz_entry_name!r}, typecode={typecode}")

        if typecode == pyimod01_archive.PYZ_ITEM_NSPKG:
            # PEP420 namespace package
            # We can use regular list for submodule_search_locations; the caller (i.e., python's PathFinder) takes care
            # of constructing _NamespacePath from it.
            spec = _frozen_importlib.ModuleSpec(fullname, None)
            spec.submodule_search_locations = [
                # NOTE: since we are using sys._MEIPASS as prefix, we need to construct path from resolved PYZ entry
                # name (equivalently, we could combine `self._path` and last part of `fullname`).
                os.path.join(sys._MEIPASS, pyz_entry_name.replace('.', os.path.sep)),
            ]
            return spec

        # Resolve full filename, as if the module/package was located on filesystem.
        origin = self.get_filename(fullname)
        is_package = typecode == pyimod01_archive.PYZ_ITEM_PKG

        spec = _frozen_importlib.ModuleSpec(
            fullname,
            self,  # loader
            is_package=is_package,
            origin=origin,
        )

        # Make the import machinery set __file__.
        # PEP 451 says: "has_location" is true if the module is locatable. In that case the spec's origin is used
        # as the location and __file__ is set to spec.origin. If additional location information is required
        # (e.g., zipimport), that information may be stored in spec.loader_state.
        spec.has_location = True

        # Set submodule_search_locations for packages. Seems to be required for importlib_resources from 3.2.0;
        # see issue #5395.
        if is_package:
            spec.submodule_search_locations = [os.path.dirname(origin)]

        return spec

    # The following methods are part of legacy PEP302 finder interface. They have been deprecated since python 3.4,
    # and removed in python 3.12. Provide compatibility shims to accommodate code that might still be using them.
    if sys.version_info[:2] < (3, 12):

        def find_loader(self, fullname):
            """
            A legacy method for finding a loader for the specified module. Returns a 2-tuple of (loader, portion) where
            portion is a sequence of file system locations contributing to part of a namespace package. The loader may
            be None while specifying portion to signify the contribution of the file system locations to a namespace
            package. An empty list can be used for portion to signify the loader is not part of a namespace package. If
            loader is None and portion is the empty list then no loader or location for a namespace package were found
            (i.e. failure to find anything for the module).

            Deprecated since python 3.4, removed in 3.12.
            """
            # Based on:
            # https://github.com/python/cpython/blob/v3.11.9/Lib/importlib/_bootstrap_external.py#L1587-L1600
            spec = self.find_spec(fullname)
            if spec is None:
                return None, []
            return spec.loader, spec.submodule_search_locations or []

        def find_module(self, fullname):
            """
            A concrete implementation of Finder.find_module() which is equivalent to self.find_loader(fullname)[0].

            Deprecated since python 3.4, removed in 3.12.
            """
            # Based on:
            # https://github.com/python/cpython/blob/v3.11.9/Lib/importlib/_bootstrap_external.py#L1585
            # https://github.com/python/cpython/blob/v3.11.9/Lib/importlib/_bootstrap_external.py#L622-L639
            #
            loader, portions = self.find_loader(fullname)
            return loader

    #-- Core PEP451 loader functionality as defined by importlib.abc.Loader
    # https://docs.python.org/3/library/importlib.html#importlib.abc.Loader
    def create_module(self, spec):
        """
        A method that returns the module object to use when importing a module. This method may return None, indicating
        that default module creation semantics should take place.

        https://docs.python.org/3/library/importlib.html#importlib.abc.Loader.create_module
        """
        return None

    def exec_module(self, module):
        """
        A method that executes the module in its own namespace when a module is imported or reloaded. The module
        should already be initialized when exec_module() is called. When this method exists, create_module()
        must be defined.

        https://docs.python.org/3/library/importlib.html#importlib.abc.Loader.exec_module
        """
        spec = module.__spec__
        bytecode = self.get_code(spec.name)
        if bytecode is None:
            raise RuntimeError(f"Failed to retrieve bytecode for {spec.name!r}!")

        # Set by the import machinery
        assert hasattr(module, '__file__')

        # If `submodule_search_locations` is not None, this is a package; set __path__.
        if spec.submodule_search_locations is not None:
            module.__path__ = spec.submodule_search_locations

        exec(bytecode, module.__dict__)

    # The following method is part of legacy PEP302 loader interface. It has been deprecated since python 3.4, and
    # slated for removal in python 3.12, although that has not happened yet. Provide compatibility shim to accommodate
    # code that might still be using it.
    if True:

        def load_module(self, fullname):
            """
            A legacy method for loading a module. If the module cannot be loaded, ImportError is raised, otherwise the
            loaded module is returned.

            Deprecated since python 3.4, slated for removal in 3.12 (but still present in python's own FileLoader in
            both v3.12.4 and v3.13.0rc1).
            """
            # Based on:
            # https://github.com/python/cpython/blob/v3.11.9/Lib/importlib/_bootstrap_external.py#L942-L945
            import importlib._bootstrap as _bootstrap
            return _bootstrap._load_module_shim(self, fullname)

    #-- PEP302 protocol extensions as defined by importlib.abc.ExecutionLoader
    # https://docs.python.org/3/library/importlib.html#importlib.abc.ExecutionLoader
    def get_filename(self, fullname):
        """
        A method that is to return the value of __file__ for the specified module. If no path is available, ImportError
        is raised.

        If source code is available, then the method should return the path to the source file, regardless of whether a
        bytecode was used to load the module.

        https://docs.python.org/3/library/importlib.html#importlib.abc.ExecutionLoader.get_filename
        """
        # Resolve fullname -> PYZ entry name (in case custom search path is in effect)
        pyz_entry_name = self._compute_pyz_entry_name(fullname)

        # Look up the PYZ entry
        entry_data = self._pyz_archive.toc.get(pyz_entry_name)
        if entry_data is None:
            raise ImportError(f'Module {fullname!r} not found in PYZ archive (entry {pyz_entry_name!r}).')
        typecode = entry_data[0]

        # NOTE: since we are using sys._MEIPASS as prefix, we need to construct path from resolved PYZ entry name
        # (equivalently, we could combine `self._path` and last part of `fullname`).
        if typecode == pyimod01_archive.PYZ_ITEM_PKG:
            return os.path.join(sys._MEIPASS, pyz_entry_name.replace('.', os.path.sep), '__init__.pyc')
        elif typecode == pyimod01_archive.PYZ_ITEM_MODULE:
            return os.path.join(sys._MEIPASS, pyz_entry_name.replace('.', os.path.sep) + '.pyc')

        # Unsupported entry type
        return None

    #-- PEP302 protocol extensions as defined by importlib.abc.InspectLoader
    # https://docs.python.org/3/library/importlib.html#importlib.abc.InspectLoader
    def get_code(self, fullname):
        """
        Return the code object for a module, or None if the module does not have a code object (as would be the case,
        for example, for a built-in module). Raise an ImportError if loader cannot find the requested module.

        https://docs.python.org/3/library/importlib.html#importlib.abc.InspectLoader.get_code
        """
        # Resolve fullname -> PYZ entry name (in case custom search path is in effect)
        pyz_entry_name = self._compute_pyz_entry_name(fullname)

        # Look up the PYZ entry - so we can raise ImportError for non-existing modules.
        entry_data = self._pyz_archive.toc.get(pyz_entry_name)
        if entry_data is None:
            raise ImportError(f'Module {fullname!r} not found in PYZ archive (entry {pyz_entry_name!r}).')

        return self._pyz_archive.extract(pyz_entry_name)

    def get_source(self, fullname):
        """
        A method to return the source of a module. It is returned as a text string using universal newlines, translating
        all recognized line separators into '\n' characters. Returns None if no source is available (e.g. a built-in
        module). Raises ImportError if the loader cannot find the module specified.

        https://docs.python.org/3/library/importlib.html#importlib.abc.InspectLoader.get_source
        """
        # Use getfilename() to obtain path to file if it were located on filesystem. This implicitly checks that the
        # fullname is valid.
        filename = self.get_filename(fullname)

        # FIXME: according to python docs "if source code is available, then the [getfilename()] method should return
        # the path to the source file, regardless of whether a bytecode was used to load the module.". At the moment,
        # our implementation always returns pyc suffix.
        filename = filename[:-1]

        try:
            # Read in binary mode, then decode
            with open(filename, 'rb') as fp:
                source_bytes = fp.read()
            return _decode_source(source_bytes)
        except FileNotFoundError:
            pass

        # Source code is unavailable.
        return None

    def is_package(self, fullname):
        """
        A method to return a true value if the module is a package, a false value otherwise. ImportError is raised if
        the loader cannot find the module.

        https://docs.python.org/3/library/importlib.html#importlib.abc.InspectLoader.is_package
        """
        # Resolve fullname -> PYZ entry name (in case custom search path is in effect)
        pyz_entry_name = self._compute_pyz_entry_name(fullname)

        # Look up the PYZ entry - so we can raise ImportError for non-existing modules.
        entry_data = self._pyz_archive.toc.get(pyz_entry_name)
        if entry_data is None:
            raise ImportError(f'Module {fullname!r} not found in PYZ archive (entry {pyz_entry_name!r}).')
        typecode = entry_data[0]

        # We do not need to worry about PEP420 namespace package entries (pyimod01_archive.PYZ_ITEM_NSPKG) here, because
        # namespace packages do not use the loader part of this importer.
        return typecode == pyimod01_archive.PYZ_ITEM_PKG

    #-- PEP302 protocol extensions as dfined by importlib.abc.ResourceLoader
    # https://docs.python.org/3/library/importlib.html#importlib.abc.ResourceLoader
    def get_data(self, path):
        """
        A method to return the bytes for the data located at path. Loaders that have a file-like storage back-end that
        allows storing arbitrary data can implement this abstract method to give direct access to the data stored.
        OSError is to be raised if the path cannot be found. The path is expected to be constructed using a module’s
        __file__ attribute or an item from a package’s __path__.

        https://docs.python.org/3/library/importlib.html#importlib.abc.ResourceLoader.get_data
        """
        # Try to fetch the data from the filesystem. Since __file__ attribute works properly, just try to open the file
        # and read it.
        with open(path, 'rb') as fp:
            return fp.read()

    #-- Support for `importlib.resources`.
    def get_resource_reader(self, fullname):
        """
        Return resource reader compatible with `importlib.resources`.
        """
        # Resolve fullname -> PYZ entry name (in case custom search path is in effect)
        pyz_entry_name = self._compute_pyz_entry_name(fullname)

        return PyiFrozenResourceReader(self, pyz_entry_name)


class PyiFrozenResourceReader:
    """
    Resource reader for importlib.resources / importlib_resources support.

    Supports only on-disk resources, which should cover the typical use cases, i.e., the access to data files;
    PyInstaller collects data files onto filesystem, and as of v6.0.0, the embedded PYZ archive is guaranteed
    to contain only .pyc modules.

    When listing resources, source .py files will not be listed as they are not collected by default. Similarly,
    sub-directories that contained only .py files are not reconstructed on filesystem, so they will not be listed,
    either. If access to .py files is required for whatever reason, they need to be explicitly collected as data files
    anyway, which will place them on filesystem and make them appear as resources.

    For on-disk resources, we *must* return path compatible with pathlib.Path() in order to avoid copy to a temporary
    file, which might break under some circumstances, e.g., metpy with importlib_resources back-port, due to:
    https://github.com/Unidata/MetPy/blob/a3424de66a44bf3a92b0dcacf4dff82ad7b86712/src/metpy/plots/wx_symbols.py#L24-L25
    (importlib_resources tries to use 'fonts/wx_symbols.ttf' as a temporary filename suffix, which fails as it contains
    a separator).

    Furthermore, some packages expect files() to return either pathlib.Path or zipfile.Path, e.g.,
    https://github.com/tensorflow/datasets/blob/master/tensorflow_datasets/core/utils/resource_utils.py#L81-L97
    This makes implementation of mixed support for on-disk and embedded resources using importlib.abc.Traversable
    protocol rather difficult.

    So in order to maximize compatibility with unfrozen behavior, the below implementation is basically equivalent of
    importlib.readers.FileReader from python 3.10:
      https://github.com/python/cpython/blob/839d7893943782ee803536a47f1d4de160314f85/Lib/importlib/readers.py#L11
    and its underlying classes, importlib.abc.TraversableResources and importlib.abc.ResourceReader:
      https://github.com/python/cpython/blob/839d7893943782ee803536a47f1d4de160314f85/Lib/importlib/abc.py#L422
      https://github.com/python/cpython/blob/839d7893943782ee803536a47f1d4de160314f85/Lib/importlib/abc.py#L312
    """
    def __init__(self, importer, name):
        # Local import to avoid including `pathlib` and its dependencies in `base_library.zip`
        from pathlib import Path
        self.importer = importer
        if self.importer.is_package(name):  # covers both normal packages and PEP-420 namespace packages
            self.path = Path(sys._MEIPASS).joinpath(*name.split('.'))
        else:
            # For modules, we should return the path to their parent (package) directory.
            self.path = Path(sys._MEIPASS).joinpath(*name.split('.')[:-1])

    def open_resource(self, resource):
        return self.files().joinpath(resource).open('rb')

    def resource_path(self, resource):
        return str(self.path.joinpath(resource))

    def is_resource(self, path):
        return self.files().joinpath(path).is_file()

    def contents(self):
        return (item.name for item in self.files().iterdir())

    def files(self):
        return self.path


class PyiFrozenEntryPointLoader:
    """
    A special loader that enables retrieval of the code-object for the __main__ module.
    """
    def __repr__(self):
        return self.__class__.__name__

    def get_code(self, fullname):
        if fullname == '__main__':
            # Special handling for __main__ module; the bootloader should store code object to _pyi_main_co
            # attribute of the module.
            return sys.modules['__main__']._pyi_main_co

        raise ImportError(f'{self} cannot handle module {fullname!r}')


def install():
    """
    Install PyInstaller's frozen finders/loaders/importers into python's import machinery.
    """
    # Setup PYZ archive reader.
    #
    # The bootloader should store the path to PYZ archive (the path to the PKG archive and the offset within it; for
    # executable-embedded archive, this is for example /path/executable_name?117568) into _pyinstaller_pyz
    # attribute of the sys module.
    global pyz_archive

    if not hasattr(sys, '_pyinstaller_pyz'):
        raise RuntimeError("Bootloader did not set sys._pyinstaller_pyz!")

    try:
        pyz_archive = pyimod01_archive.ZlibArchiveReader(sys._pyinstaller_pyz, check_pymagic=True)
    except Exception as e:
        raise RuntimeError("Failed to setup PYZ archive reader!") from e

    delattr(sys, '_pyinstaller_pyz')

    # On Windows, there is finder called `_frozen_importlib.WindowsRegistryFinder`, which looks for Python module
    # locations in Windows registry. The frozen application should not look for those, so remove this finder
    # from `sys.meta_path`.
    for entry in sys.meta_path:
        if getattr(entry, '__name__', None) == 'WindowsRegistryFinder':
            sys.meta_path.remove(entry)
            break

    # Insert our hook for `PyiFrozenImporter` into `sys.path_hooks`. Place it after `zipimporter`, if available.
    for idx, entry in enumerate(sys.path_hooks):
        if getattr(entry, '__name__', None) == 'zipimporter':
            trace(f"PyInstaller: inserting our finder hook at index {idx + 1} in sys.path_hooks.")
            sys.path_hooks.insert(idx + 1, PyiFrozenImporter.path_hook)
            break
    else:
        trace("PyInstaller: zipimporter hook not found in sys.path_hooks! Prepending our finder hook to the list.")
        sys.path_hooks.insert(0, PyiFrozenImporter.path_hook)

    # Python might have already created a `FileFinder` for `sys._MEIPASS`. Remove the entry from path importer cache,
    # so that next loading attempt creates `PyiFrozenImporter` instead. This could probably be avoided altogether if
    # we refrained from adding `sys._MEIPASS` to `sys.path` until our importer hooks is in place.
    sys.path_importer_cache.pop(sys._MEIPASS, None)

    # Set the PyiFrozenEntryPointLoader as loader for __main__, in order for python to treat __main__ as a module
    # instead of a built-in, and to allow its code object to be retrieved.
    try:
        sys.modules['__main__'].__loader__ = PyiFrozenEntryPointLoader()
    except Exception:
        pass

    # Apply hack for python >= 3.11 and its frozen stdlib modules.
    if sys.version_info >= (3, 11):
        _fixup_frozen_stdlib()


# A hack for python >= 3.11 and its frozen stdlib modules. Unless `sys._stdlib_dir` is set, these modules end up
# missing __file__ attribute, which causes problems with 3rd party code. At the time of writing, python interpreter
# configuration API does not allow us to influence `sys._stdlib_dir` - it always resets it to `None`. Therefore,
# we manually set the path, and fix __file__ attribute on modules.
def _fixup_frozen_stdlib():
    import _imp  # built-in

    # If sys._stdlib_dir is None or empty, override it with sys._MEIPASS
    if not sys._stdlib_dir:
        try:
            sys._stdlib_dir = sys._MEIPASS
        except AttributeError:
            pass

    # The sys._stdlib_dir set above should affect newly-imported python-frozen modules. However, most of them have
    # been already imported during python initialization and our bootstrap, so we need to retroactively fix their
    # __file__ attribute.
    for module_name, module in sys.modules.items():
        if not _imp.is_frozen(module_name):
            continue

        is_pkg = _imp.is_frozen_package(module_name)

        # Determine "real" name from __spec__.loader_state.
        loader_state = module.__spec__.loader_state

        orig_name = loader_state.origname
        if is_pkg:
            orig_name += '.__init__'

        # We set suffix to .pyc to be consistent with our PyiFrozenImporter.
        filename = os.path.join(sys._MEIPASS, *orig_name.split('.')) + '.pyc'

        # Fixup the __file__ attribute
        if not hasattr(module, '__file__'):
            try:
                module.__file__ = filename
            except AttributeError:
                pass

        # Fixup the loader_state.filename
        # Except for _frozen_importlib (importlib._bootstrap), whose loader_state.filename appears to be left at
        # None in python.
        if loader_state.filename is None and orig_name != 'importlib._bootstrap':
            loader_state.filename = filename
