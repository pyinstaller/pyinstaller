#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
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
# Import *ONLY* builtin modules.
# List of built-in modules: sys.builtin_module_names

import sys

import _frozen_importlib
import pyimod01_os_path as pyi_os_path
from pyimod02_archive import ArchiveReadError, ZlibArchiveReader

SYS_PREFIX = sys._MEIPASS + pyi_os_path.os_sep
SYS_PREFIXLEN = len(SYS_PREFIX)

# In Python 3, it is recommended to use class 'types.ModuleType' to create a new module. However, 'types' module is
# not a built-in module. The 'types' module uses this trick with using type() function:
imp_new_module = type(sys)

if sys.flags.verbose and sys.stderr:

    def trace(msg, *a):
        sys.stderr.write(msg % a)
        sys.stderr.write("\n")
else:

    def trace(msg, *a):
        pass


class FrozenPackageImporter(object):
    """
    Wrapper class for FrozenImporter that imports one specific fullname from a module named by an alternate fullname.
    The alternate fullname is derived from the __path__ of the package module containing that module.

    This is called by FrozenImporter.find_module whenever a module is found as a result of searching module.__path__
    """
    def __init__(self, importer, entry_name):
        self._entry_name = entry_name
        self._importer = importer

    def load_module(self, fullname):
        # Deprecated in Python 3.4, see PEP-451.
        return self._importer.load_module(fullname, self._entry_name)


def _decode_source(source_bytes):
    """
    Decode bytes representing source code and return the string. Universal newline support is used in the decoding.
    Based on CPython's implementation of the same functionality:
    https://github.com/python/cpython/blob/3.9/Lib/importlib/_bootstrap_external.py#L679-L688
    """
    # Local imports to avoid bootstrap issues
    # NOTE: both modules are listed in compat.PY3_BASE_MODULES and collected into base_library.zip.
    import io
    import tokenize

    source_bytes_readline = io.BytesIO(source_bytes).readline
    encoding = tokenize.detect_encoding(source_bytes_readline)
    newline_decoder = io.IncrementalNewlineDecoder(decoder=None, translate=True)
    return newline_decoder.decode(source_bytes.decode(encoding[0]))


class FrozenImporter(object):
    """
    Load bytecode of Python modules from the executable created by PyInstaller.

    Python bytecode is zipped and appended to the executable.

    NOTE: PYZ format cannot be replaced by zipimport module.

    The problem is that we have no control over zipimport; for instance, it does not work if the zip file is embedded
    into a PKG that is appended to an executable, like we create in one-file mode.

    This is PEP-302 finder and loader class for the ``sys.meta_path`` hook. A PEP-302 finder requires method
    find_module() to return loader class with method load_module(). Both these methods are implemented in one class.

    This is also a PEP-451 finder and loader class for the ModuleSpec type import system. A PEP-451 finder requires
    method find_spec(), a PEP-451 loader requires methods exec_module(), load_module(9 and (optionally) create_module().
    All these methods are implemented in this one class.

    To use this class just call:
        FrozenImporter.install()
    """
    def __init__(self):
        """
        Load, unzip and initialize the Zip archive bundled with the executable.
        """
        # Examine all items in sys.path and the one like /path/executable_name?117568 is the correct executable with
        # the bundled zip archive. Use this value for the ZlibArchiveReader class, and remove this item from sys.path.
        # It was needed only for FrozenImporter class. Wrong path from sys.path raises an ArchiveReadError exception.
        for pyz_filepath in sys.path:
            try:
                # Unzip zip archive bundled with the executable.
                self._pyz_archive = ZlibArchiveReader(pyz_filepath)
                # Verify the integrity of the zip archive with Python modules.
                # This is already done when creating the ZlibArchiveReader instance.
                #self._pyz_archive.checkmagic()

                # As no Exception was raised, we can assume that ZlibArchiveReader was successfully loaded.
                # Let's remove 'pyz_filepath' from sys.path.
                sys.path.remove(pyz_filepath)
                # Some runtime hook might need access to the list of available frozen modules. Let's make them
                # accessible as a set().
                self.toc = set(self._pyz_archive.toc.keys())
                # Return - no error was raised.
                trace("# PyInstaller: FrozenImporter(%s)", pyz_filepath)
                return
            except IOError:
                # Item from sys.path is not ZlibArchiveReader; let's try next one.
                continue
            except ArchiveReadError:
                # Item from sys.path is not ZlibArchiveReader; let's try next one.
                continue
        # sys.path does not contain the filename of the executable with the bundled zip archive. Raise import error.
        raise ImportError("Cannot load frozen modules.")

    # Private helper
    def _is_pep420_namespace_package(self, fullname):
        if fullname in self.toc:
            try:
                return self._pyz_archive.is_pep420_namespace_package(fullname)
            except Exception as e:
                raise ImportError('Loader FrozenImporter cannot handle module ' + fullname) from e
        else:
            raise ImportError('Loader FrozenImporter cannot handle module ' + fullname)

    def find_module(self, fullname, path=None):
        # Deprecated in Python 3.4, see PEP-451
        """
        PEP-302 finder.find_module() method for the ``sys.meta_path`` hook.

        fullname     fully qualified name of the module
        path         None for a top-level module, or package.__path__ for submodules or subpackages.

        Return a loader object if the module was found, or None if it was not. If find_module() raises an exception,
        it will be propagated to the caller, aborting the import.
        """
        module_loader = None  # None means - no module found in this importer.

        if fullname in self.toc:
            # Tell the import machinery to use self.load_module() to load the module.
            module_loader = self
            trace("import %s # PyInstaller PYZ", fullname)
        elif path is not None:
            # Try to handle module.__path__ modifications by the modules themselves.
            # Reverse the fake __path__ we added to the package module to a dotted module name, and add the tail module
            # from fullname onto that to synthesize a new fullname.
            modname = fullname.split('.')[-1]

            for p in path:
                if not p.startswith(SYS_PREFIX):
                    continue
                p = p[SYS_PREFIXLEN:]
                parts = p.split(pyi_os_path.os_sep)
                if not parts:
                    continue
                if not parts[0]:
                    parts = parts[1:]
                parts.append(modname)
                entry_name = ".".join(parts)
                if entry_name in self.toc:
                    module_loader = FrozenPackageImporter(self, entry_name)
                    trace("import %s as %s # PyInstaller PYZ (__path__ override: %s)", entry_name, fullname, p)
                    break
        # Release the interpreter's import lock.
        if module_loader is None:
            trace("# %s not found in PYZ", fullname)
        return module_loader

    def load_module(self, fullname, entry_name=None):
        # Deprecated in Python 3.4, see PEP-451
        """
        PEP-302 loader.load_module() method for the ``sys.meta_path`` hook.

        Return the loaded module (instance of imp_new_module()) or raise an exception, preferably ImportError if an
        existing exception is not being propagated.

        When called from FrozenPackageImporter, `entry_name` is the name of the module as it is stored in the archive.
        This module will be loaded and installed into sys.modules using `fullname` as its name.
        """
        # Acquire the interpreter's import lock.
        module = None
        if entry_name is None:
            entry_name = fullname
        try:
            # PEP302: if there is an existing module object named 'fullname' in sys.modules, the loader must use that
            # existing module.
            module = sys.modules.get(fullname)

            # Module not in sys.modules - load it and add it to sys.modules.
            if module is None:
                # Load code object from the bundled ZIP archive.
                is_pkg, bytecode = self._pyz_archive.extract(entry_name)
                # Create new empty 'module' object.
                module = imp_new_module(fullname)

                # TODO: replace bytecode.co_filename by something more meaningful:
                # e.g., /absolute/path/frozen_executable/path/to/module/module_name.pyc
                # Paths from developer machine are masked.

                # Set __file__ attribute of a module relative to the executable, so that data files can be found.
                module.__file__ = self.get_filename(entry_name)

                #-- Set __path__  if 'fullname' is a package.
                # Python has modules and packages. A Python package is a container for several modules or packages.
                if is_pkg:
                    # If a module has a __path__ attribute, the import mechanism will treat it as a package.
                    #
                    # Since PYTHONHOME is set in bootloader, 'sys.prefix' points to the correct path where PyInstaller
                    # should find bundled dynamic libraries. In one-file mode it points to the tmp directory where
                    # bundled files are extracted at execution time.
                    #
                    # __path__ cannot be empty list because 'wx' module prepends something to it. It cannot contain
                    # value 'sys.prefix' because 'xml.etree.cElementTree' fails otherwise.
                    #
                    # Set __path__ to point to 'sys.prefix/package/subpackage'.
                    module.__path__ = [pyi_os_path.os_path_dirname(module.__file__)]

                #-- Set __loader__
                # The attribute __loader__ improves support for module 'pkg_resources' and enables the following
                # functions within the frozen app: pkg_resources.resource_string(), pkg_resources.resource_stream().
                module.__loader__ = self

                #-- Set __package__
                # Accoring to PEP302, this attribute must be set. When it is present, relative imports will be based
                # on this attribute rather than the module __name__ attribute. More details can be found in PEP366.
                # For ordinary modules, this is set like: 'aa.bb.cc.dd' -> 'aa.bb.cc'
                if is_pkg:
                    module.__package__ = fullname
                else:
                    module.__package__ = fullname.rsplit('.', 1)[0]

                #-- Set __spec__
                # Python 3.4 introduced module attribute __spec__ to consolidate all module attributes.
                module.__spec__ = _frozen_importlib.ModuleSpec(entry_name, self, is_package=is_pkg)

                #-- Add module object to sys.modules dictionary.
                # Module object must be in sys.modules before the loader executes the module code. This is crucial
                # because the module code may (directly or indirectly) import itself; adding it to sys.modules
                # beforehand prevents unbounded recursion in the worst case and multiple loading in the best.
                sys.modules[fullname] = module

                # Run the module code.
                exec(bytecode, module.__dict__)
                # Reread the module from sys.modules in case it has changed itself.
                module = sys.modules[fullname]

        except Exception:
            # Remove 'fullname' from sys.modules if it was appended there.
            if fullname in sys.modules:
                sys.modules.pop(fullname)
            # TODO: do we need to raise different types of Exceptions for better debugging?
            # PEP302 requires to raise ImportError exception.
            #raise ImportError("Can't load frozen module: %s" % fullname)
            raise

        # Module returned only in case of no exception.
        return module

    #-- Optional Extensions to the PEP-302 Importer Protocol --

    def is_package(self, fullname):
        if fullname in self.toc:
            try:
                return self._pyz_archive.is_package(fullname)
            except Exception as e:
                raise ImportError('Loader FrozenImporter cannot handle module ' + fullname) from e
        else:
            raise ImportError('Loader FrozenImporter cannot handle module ' + fullname)

    def get_code(self, fullname):
        """
        Get the code object associated with the module.

        ImportError should be raised if module not found.
        """
        try:
            if fullname == '__main__':
                # Special handling for __main__ module; the bootloader should store code object to _pyi_main_co
                # attribute of the module.
                return sys.modules['__main__']._pyi_main_co

            # extract() returns None if fullname is not in the archive, and the subsequent subscription attempt raises
            # exception, which is turned into ImportError.
            return self._pyz_archive.extract(fullname)[1]
        except Exception as e:
            raise ImportError('Loader FrozenImporter cannot handle module ' + fullname) from e

    def get_source(self, fullname):
        """
        Method should return the source code for the module as a string.
        But frozen modules does not contain source code.

        Return None, unless the corresponding source file was explicitly collected to the filesystem.
        """
        if fullname in self.toc:
            # Try loading the .py file from the filesystem (only for collected modules)
            if self.is_package(fullname):
                fullname += '.__init__'
            filename = pyi_os_path.os_path_join(SYS_PREFIX, fullname.replace('.', pyi_os_path.os_sep) + '.py')
            try:
                # Read in binary mode, then decode
                with open(filename, 'rb') as fp:
                    source_bytes = fp.read()
                return _decode_source(source_bytes)
            except FileNotFoundError:
                pass
            return None
        else:
            # ImportError should be raised if module not found.
            raise ImportError('No module named ' + fullname)

    def get_data(self, path):
        """
        Returns the data as a string, or raises IOError if the "file" was not found. The data is always returned as if
        "binary" mode was used.

        This method is useful for getting resources with 'pkg_resources' that are bundled with Python modules in the
        PYZ archive.

        The 'path' argument is a path that can be constructed by munging module.__file__ (or pkg.__path__ items).
        """
        assert path.startswith(SYS_PREFIX)
        fullname = path[SYS_PREFIXLEN:]
        if fullname in self.toc:
            # If the file is in the archive, return this
            return self._pyz_archive.extract(fullname)[1]
        else:
            # Otherwise try to fetch it from the filesystem. Since __file__ attribute works properly, just try to open
            # and read it.
            with open(path, 'rb') as fp:
                return fp.read()

    def get_filename(self, fullname):
        """
        This method should return the value that __file__ would be set to if the named module was loaded. If the module
        is not found, an ImportError should be raised.
        """
        # The absolute absolute path to the executable is taken from sys.prefix. In onefile mode it points to the temp
        # directory where files are unpacked by PyInstaller. Then, append the appropriate suffix (__init__.pyc for a
        # package, or just .pyc for a module).
        # Method is_package() will raise ImportError if module not found.
        if self.is_package(fullname):
            filename = pyi_os_path.os_path_join(
                pyi_os_path.os_path_join(SYS_PREFIX, fullname.replace('.', pyi_os_path.os_sep)), '__init__.pyc'
            )
        else:
            filename = pyi_os_path.os_path_join(SYS_PREFIX, fullname.replace('.', pyi_os_path.os_sep) + '.pyc')
        return filename

    def find_spec(self, fullname, path=None, target=None):
        """
        PEP-451 finder.find_spec() method for the ``sys.meta_path`` hook.

        fullname     fully qualified name of the module
        path         None for a top-level module, or package.__path__ for
                     submodules or subpackages.
        target       unused by this Finder

        Finders are still responsible for identifying, and typically creating, the loader that should be used to load a
        module. That loader will now be stored in the module spec returned by find_spec() rather than returned directly.
        As is currently the case without the PEP-452, if a loader would be costly to create, that loader can be designed
        to defer the cost until later.

        Finders must return ModuleSpec objects when find_spec() is called. This new method replaces find_module() and
        find_loader() (in the PathEntryFinder case). If a loader does not have find_spec(), find_module() and
        find_loader() are used instead, for backward-compatibility.
        """
        entry_name = None  # None means - no module found in this importer.

        if fullname in self.toc:
            entry_name = fullname
            trace("import %s # PyInstaller PYZ", fullname)
        elif path is not None:
            # Try to handle module.__path__ modifications by the modules themselves.
            # Reverse the fake __path__ we added to the package module into a dotted module name, and add the tail
            # module from fullname onto that to synthesize a new fullname.
            modname = fullname.rsplit('.')[-1]

            for p in path:
                if not p.startswith(SYS_PREFIX):
                    continue
                p = p[SYS_PREFIXLEN:]
                parts = p.split(pyi_os_path.os_sep)
                if not parts:
                    continue
                if not parts[0]:
                    parts = parts[1:]
                parts.append(modname)
                entry_name = ".".join(parts)
                if entry_name in self.toc:
                    trace("import %s as %s # PyInstaller PYZ (__path__ override: %s)", entry_name, fullname, p)
                    break
            else:
                entry_name = None

        if entry_name is None:
            trace("# %s not found in PYZ", fullname)
            return None

        if self._is_pep420_namespace_package(entry_name):
            # PEP-420 namespace package; as per PEP 451, we need to return a spec with "loader" set to None
            # (a.k.a. not set)
            spec = _frozen_importlib.ModuleSpec(fullname, None, is_package=True)
            # Set submodule_search_locations, which seems to fill the __path__ attribute.
            spec.submodule_search_locations = [pyi_os_path.os_path_dirname(self.get_filename(entry_name))]
            return spec

        # origin has to be the filename
        origin = self.get_filename(entry_name)
        is_pkg = self.is_package(entry_name)

        spec = _frozen_importlib.ModuleSpec(
            fullname,
            self,
            is_package=is_pkg,
            origin=origin,
            # Provide the entry_name for the loader to use during loading.
            loader_state=entry_name
        )

        # Make the import machinery set __file__.
        # PEP 451 says: "has_location" is true if the module is locatable. In that case the spec's origin is used
        # as the location and __file__ is set to spec.origin. If additional location information is required
        # (e.g., zipimport), that information may be stored in spec.loader_state.
        spec.has_location = True

        # Set submodule_search_locations for packages. Seems to be required for importlib_resources from 3.2.0;
        # see issue #5395.
        if is_pkg:
            spec.submodule_search_locations = [pyi_os_path.os_path_dirname(self.get_filename(entry_name))]

        return spec

    def create_module(self, spec):
        """
        PEP-451 loader.create_module() method for the ``sys.meta_path`` hook.

        Loaders may also implement create_module() that will return a new module to exec. It may return None to indicate
        that the default module creation code should be used. One use case, though atypical, for create_module() is to
        provide a module that is a subclass of the builtin module type. Most loaders will not need to implement
        create_module().

        create_module() should properly handle the case where it is called more than once for the same spec/module. This
        may include returning None or raising ImportError.
        """
        # Contrary to what is defined in PEP-451, this method is not optional. We want the default results, so we simply
        # return None (which is handled for su my the import machinery).
        # See https://bugs.python.org/issue23014 for more information.
        return None

    def exec_module(self, module):
        """
        PEP-451 loader.exec_module() method for the ``sys.meta_path`` hook.

        Loaders will have a new method, exec_module(). Its only job is to "exec" the module and consequently populate
        the module's namespace. It is not responsible for creating or preparing the module object, nor for any cleanup
        afterward. It has no return value. exec_module() will be used during both loading and reloading.

        exec_module() should properly handle the case where it is called more than once. For some kinds of modules this
        may mean raising ImportError every time after the first time the method is called. This is particularly relevant
        for reloading, where some kinds of modules do not support in-place reloading.
        """
        spec = module.__spec__
        bytecode = self.get_code(spec.loader_state)

        # Set by the import machinery
        assert hasattr(module, '__file__')

        # If `submodule_search_locations` is not None, this is a package; set __path__.
        if spec.submodule_search_locations is not None:
            # Since PYTHONHOME is set in bootloader, 'sys.prefix' points to the correct path where PyInstaller should
            # find bundled dynamic libraries. In one-file mode it points to the tmp directory where bundled files are
            # extracted at execution time.
            #
            # __path__ cannot be empty list because 'wx' module prepends something to it. It cannot contain value
            # 'sys.prefix' because 'xml.etree.cElementTree' fails otherwise.
            #
            # Set __path__ to point to 'sys.prefix/package/subpackage'.
            module.__path__ = [pyi_os_path.os_path_dirname(module.__file__)]

        exec(bytecode, module.__dict__)

    def get_resource_reader(self, fullname):
        """
        Return importlib.resource-compatible resource reader.
        """
        return FrozenResourceReader(self, fullname)


class FrozenResourceReader:
    """
    Resource reader for importlib.resources / importlib_resources support.

    Currently supports only on-disk resources (support for resources from the embedded archive is missing).
    However, this should cover the typical use cases (access to data files), as PyInstaller collects data files onto
    filesystem, and only .pyc modules are collected into embedded archive. One exception are resources collected from
    zipped eggs (which end up collected into embedded archive), but those should be rare anyway.

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
        import pathlib  # Local import to avoid bootstrap issues.
        self.importer = importer
        self.path = pathlib.Path(sys._MEIPASS).joinpath(*name.split('.'))

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


def install():
    """
    Install FrozenImporter class and other classes into the import machinery.

    This function installs the FrozenImporter class into the import machinery of the running process. The importer is
    added to sys.meta_path. It could be added to sys.path_hooks, but sys.meta_path is processed by Python before
    looking at sys.path!

    The order of processing import hooks in sys.meta_path:

    1. built-in modules
    2. modules from the bundled ZIP archive
    3. C extension modules
    4. Modules from sys.path
    """
    # Ensure Python looks in the bundled zip archive for modules before any other places.
    fimp = FrozenImporter()
    sys.meta_path.append(fimp)

    # On Windows there is importer _frozen_importlib.WindowsRegistryFinder that looks for Python modules in Windows
    # registry. The frozen executable should not look for anything in the Windows registry. Remove this importer
    # from sys.meta_path.
    for item in sys.meta_path:
        if hasattr(item, '__name__') and item.__name__ == 'WindowsRegistryFinder':
            sys.meta_path.remove(item)
            break
    # _frozen_importlib.PathFinder is also able to handle Python C extensions. However, PyInstaller needs its own
    # importer as it uses extension names like 'module.submodle.so' (instead of paths). As of Python 3.7.0b2, there
    # are several PathFinder instances (and duplicate ones) on sys.meta_path. This propobly is a bug, see
    # https://bugs.python.org/issue33128. Thus we need to move all of them to the end, and eliminate the duplicates.
    pathFinders = []
    for item in reversed(sys.meta_path):
        if getattr(item, '__name__', None) == 'PathFinder':
            sys.meta_path.remove(item)
            if item not in pathFinders:
                pathFinders.append(item)
    sys.meta_path.extend(reversed(pathFinders))
    # TODO: do we need _frozen_importlib.FrozenImporter in Python 3? Could it be also removed?

    # Set the FrozenImporter as loader for __main__, in order for python to treat __main__ as a module instead of
    # a built-in.
    try:
        sys.modules['__main__'].__loader__ = fimp
    except Exception:
        pass
