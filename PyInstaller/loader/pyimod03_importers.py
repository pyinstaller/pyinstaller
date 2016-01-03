#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
PEP-302 importers for frozen applications.
"""


### **NOTE** This module is used during bootstrap.
### Import *ONLY* builtin modules.
### List of built-in modules: sys.builtin_module_names



import sys
import pyimod01_os_path as pyi_os_path

from pyimod02_archive import ArchiveReadError, ZlibArchiveReader


SYS_PREFIX = sys._MEIPASS
SYS_PREFIXLEN = len(SYS_PREFIX)

# In Python 3.3+ tne locking scheme has changed to per-module locks for the most part.
# Global locking should not be required in Python 3.3+
if sys.version_info[0:2] < (3, 3):
    # TODO Implement this for Python 3.2 - 'imp' is not a built-in module anymore.
    import imp
    imp_lock = imp.acquire_lock
    imp_unlock = imp.release_lock
    # Find the platform specific extension suffixes.
    # For Python 2 we need the info-tuples for loading
    EXTENSION_SUFFIXES = dict((f[0], f) for f in imp.get_suffixes()
                              if f[2] == imp.C_EXTENSION)
    # Function to create a new module object from pyz archive.
    imp_new_module = imp.new_module
else:
    # Dumb locking functions - do nothing.
    def imp_lock(): pass
    def imp_unlock(): pass
    import _frozen_importlib
    if sys.version_info[1] <= 4:
        # Python 3.3, 3.4
        EXTENSION_SUFFIXES = _frozen_importlib.EXTENSION_SUFFIXES
        EXTENSION_LOADER = _frozen_importlib.ExtensionFileLoader
    else:
        # Since Python 3.5+ some attributes were moved to '_bootstrap_external'.
        EXTENSION_SUFFIXES = _frozen_importlib._bootstrap_external.EXTENSION_SUFFIXES
        EXTENSION_LOADER = _frozen_importlib._bootstrap_external.ExtensionFileLoader

    # In Python 3 it is recommended to use class 'types.ModuleType' to create a new module.
    # However, 'types' module is not a built-in module. The 'types' module uses this trick
    # with using type() function:
    imp_new_module = type(sys)

if sys.flags.verbose:
    def trace(msg, *a):
        sys.stderr.write(msg % a)
        sys.stderr.write("\n")
else:
    def trace(msg, *a):
        pass

# TODO Do we still need BuiltintImporter for Python 3 built-in modules?
class BuiltinImporter(object):
    """
    PEP-302 wrapper of the built-in modules for sys.meta_path.

    This wrapper ensures that import machinery will not look for built-in
    modules in the bundled ZIP archive.
    """
    def find_module(self, fullname, path=None):
        imp_lock()
        module_loader = None  # None means - no module found by this importer.

        # Look in the list of built-in modules.
        if fullname in sys.builtin_module_names:
            module_loader = self

        imp_unlock()
        return module_loader

    def load_module(self, fullname, path=None):
        imp_lock()

        try:
            # PEP302 If there is an existing module object named 'fullname'
            # in sys.modules, the loader must use that existing module.
            module = sys.modules.get(fullname)
            if module is None:
                module = imp.init_builtin(fullname)

        except Exception:
            # Remove 'fullname' from sys.modules if it was appended there.
            if fullname in sys.modules:
                sys.modules.pop(fullname)
            raise  # Raise the same exception again.

        finally:
            # Release the interpreter's import lock.
            imp_unlock()

        return module

    ### Optional Extensions to the PEP-302 Importer Protocol

    def is_package(self, fullname):
        """
        Return always False since built-in modules are never packages.
        """
        if fullname in sys.builtin_module_names:
            return False
        else:
            # ImportError should be raised if module not found.
            raise ImportError('No module named ' + fullname)

    def get_code(self, fullname):
        """
        Return None for a built-in module.
        """
        if fullname in sys.builtin_module_names:
            return None
        else:
            # ImportError should be raised if module not found.
            raise ImportError('No module named ' + fullname)

    def get_source(self, fullname):
        """
        Return None for a built-in module.
        """
        if fullname in sys.builtin_module_names:
            return None
        else:
            # ImportError should be raised if module not found.
            raise ImportError('No module named ' + fullname)


class FrozenPackageImporter(object):
    """
    Wrapper class for FrozenImporter that imports one specific fullname from
    a module named by an alternate fullname. The alternate fullname is derived from the
    __path__ of the package module containing that module.

    This is called by FrozenImporter.find_module whenever a module is found as a result
    of searching module.__path__
    """
    def __init__(self, importer, fullname):
        self._fullname = fullname
        self._importer = importer

    def load_module(self, fullname):
        return self._importer.load_module(fullname, self._fullname)


class FrozenImporter(object):
    """
    Load bytecode of Python modules from the executable created by PyInstaller.

    Python bytecode is zipped and appended to the executable.

    NOTE: PYZ format cannot be replaced by zipimport module.

    The problem is that we have no control over zipimport; for instance,
    it doesn't work if the zip file is embedded into a PKG appended
    to an executable, like we create in one-file.

    This is PEP-302 finder and loader class for the ``sys.meta_path`` hook.
    A PEP-302 finder requires method find_module() to return loader
    class with method load_module(). Both these methods are implemented
    in one class.


    To use this class just call

        FrozenImporter.install()
    """
    def __init__(self):
        """
        Load, unzip and initialize the Zip archive bundled with the executable.
        """
        # Examine all items in sys.path and the one like /path/executable_name?117568
        # is the correct executable with bundled zip archive. Use this value
        # for the ZlibArchiveReader class and remove this item from sys.path.
        # It was needed only for FrozenImporter class. Wrong path from sys.path
        # Raises ArchiveReadError exception.
        for pyz_filepath in sys.path:
            # We need to acquire the interpreter's import lock here
            # because ZlibArchiveReader() seeks through and reads from the
            # zip archive.
            imp_lock()
            try:
                # Unzip zip archive bundled with the executable.
                self._pyz_archive = ZlibArchiveReader(pyz_filepath)
                # Verify the integrity of the zip archive with Python modules.
                # This is already done when creating the ZlibArchiveReader instance.
                #self._pyz_archive.checkmagic()

                # End this method since no Exception was raised we can assume
                # ZlibArchiveReader was successfully loaded. Let's remove 'pyz_filepath'
                # from sys.path.
                sys.path.remove(pyz_filepath)
                # Some runtime hook might need access to the list of available
                # frozen module. Let's make them accessible as a set().
                self.toc = set(self._pyz_archive.toc.keys())
                # Return - no error was raised.
                trace("# PyInstaller: FrozenImporter(%s)", pyz_filepath)
                return
            except IOError:
                # Item from sys.path is not ZlibArchiveReader let's try next.
                continue
            except ArchiveReadError:
                # Item from sys.path is not ZlibArchiveReader let's try next.
                continue
            finally:
                imp_unlock()
        # sys.path does not contain filename of executable with bundled zip archive.
        # Raise import error.
        raise ImportError("Can't load frozen modules.")


    def __call__(self, path):
        """
        PEP-302 sys.path_hook processor.

        sys.path_hook is a list of callables, which will be checked in
        sequence to determine if they can handle a given path item.
        """

        if path.startswith(SYS_PREFIX):
            fullname = path[SYS_PREFIXLEN+1:].replace(pyi_os_path.os_sep, '.')
            loader = self.find_module(fullname)
            if loader is not None:
                return loader
        raise ImportError(path)


    def find_module(self, fullname, path=None):
        """
        PEP-302 finder.find_module() method for the ``sys.meta_path`` hook.

        fullname     fully qualified name of the module
        path         None for a top-level module, or package.__path__ for submodules or subpackages.

        Return a loader object if the module was found, or None if it wasn't. If find_module() raises
        an exception, it will be propagated to the caller, aborting the import.
        """
        # Acquire the interpreter's import lock for the current thread. This
        # lock should be used by import hooks to ensure thread-safety when
        # importing modules.

        imp_lock()
        module_loader = None  # None means - no module found in this importer.

        if fullname in self.toc:
            # Tell the import machinery to use self.load_module() to load the module.
            module_loader = self
            trace("import %s # PyInstaller PYZ", fullname)
        elif path is not None:
            # Try to handle module.__path__ modifications by the modules themselves
            # Reverse the fake __path__ we added to the package module to a
            # dotted module name and add the tail module from fullname onto that
            # to synthesize a new fullname
            modname = fullname.split('.')[-1]

            for p in path:
                p = p.replace(SYS_PREFIX, "")
                parts = p.split(pyi_os_path.os_sep)
                if not len(parts): continue
                if not parts[0]:
                    parts = parts[1:]
                parts.append(modname)
                real_fullname = ".".join(parts)
                if real_fullname in self.toc:
                    module_loader = FrozenPackageImporter(self, real_fullname)
                    trace("import %s as %s # PyInstaller PYZ (__path__ override: %s)",
                          real_fullname, fullname, p)
                    break
        # Release the interpreter's import lock.
        imp_unlock()
        if module_loader is None:
            trace("# %s not found in PYZ", fullname)
        return module_loader

    def load_module(self, fullname, real_fullname=None):
        """
        PEP-302 loader.load_module() method for the ``sys.meta_path`` hook.

        Return the loaded module (instance of imp_new_module()) or raises
        an exception, preferably ImportError if an existing exception
        is not being propagated.

        When called from FrozenPackageImporter, `real_fullname` is the name of the
        module as it is stored in the archive. This module will be loaded and installed
        into sys.modules using `fullname` as its name
        """
        # Acquire the interpreter's import lock.
        imp_lock()
        module = None
        if real_fullname is None:
            real_fullname=fullname
        try:
            # PEP302 If there is an existing module object named 'fullname'
            # in sys.modules, the loader must use that existing module.
            module = sys.modules.get(fullname)

            # Module not in sys.modules - load it and it to sys.modules.
            if module is None:
                # Load code object from the bundled ZIP archive.
                is_pkg, bytecode = self._pyz_archive.extract(real_fullname)
                # Create new empty 'module' object.
                module = imp_new_module(fullname)

                # TODO Replace bytecode.co_filename by something more meaningful:
                # e.g. /absolute/path/frozen_executable/path/to/module/module_name.pyc
                # Paths from developer machine are masked.

                ### Set __file__ attribute of a module relative to the executable
                # so that data files can be found. The absolute absolute path
                # to the executable is taken from sys.prefix. In onefile mode it
                # points to the temp directory where files are unpacked by PyInstaller.
                # Then, append the appropriate suffix (__init__.pyc for a package, or just .pyc for a module).
                if is_pkg:
                    module.__file__ = pyi_os_path.os_path_join(pyi_os_path.os_path_join(SYS_PREFIX,
                        fullname.replace('.', pyi_os_path.os_sep)), '__init__.pyc')
                else:
                    module.__file__ = pyi_os_path.os_path_join(SYS_PREFIX,
                        fullname.replace('.', pyi_os_path.os_sep) + '.pyc')

                ### Set __path__  if 'fullname' is a package.
                # Python has modules and packages. A Python package is container
                # for several modules or packages.
                if is_pkg:

                    # If a module has a __path__ attribute, the import mechanism
                    # will treat it as a package.
                    #
                    # Since PYTHONHOME is set in bootloader, 'sys.prefix' points to the
                    # correct path where PyInstaller should find bundled dynamic
                    # libraries. In one-file mode it points to the tmp directory where
                    # bundled files are extracted at execution time.
                    #
                    # __path__ cannot be empty list because 'wx' module prepends something to it.
                    # It cannot contain value 'sys.prefix' because 'xml.etree.cElementTree' fails
                    # Otherwise.
                    #
                    # Set __path__ to point to 'sys.prefix/package/subpackage'.
                    module.__path__ = [pyi_os_path.os_path_dirname(module.__file__)]

                ### Set __loader__
                # The attribute __loader__ improves support for module 'pkg_resources' and
                # with the frozen apps the following functions are working:
                # pkg_resources.resource_string(), pkg_resources.resource_stream().
                module.__loader__ = self

                ### Set __package__
                # Accoring to PEP302 this attribute must be set.
                # When it is present, relative imports will be based on this
                # attribute rather than the module __name__ attribute.
                # More details can be found in PEP366.
                # For ordinary modules this is set like:
                #     'aa.bb.cc.dd'  ->  'aa.bb.cc'
                if is_pkg:
                    module.__package__ = fullname
                else:
                    module.__package__ = fullname.rsplit('.', 1)[0]

                ### Set __spec__ for Python 3.4+
                # In Python 3.4 was introduced module attribute __spec__ to
                # consolidate all module attributes.
                if sys.version_info[0:2] > (3, 3):
                    module.__spec__ = _frozen_importlib.ModuleSpec(
                        real_fullname, self, is_package=is_pkg)

                ### Add module object to sys.modules dictionary.
                # Module object must be in sys.modules before the loader
                # executes the module code. This is crucial because the module
                # code may (directly or indirectly) import itself; adding it
                # to sys.modules beforehand prevents unbounded recursion in the
                # worst case and multiple loading in the best.
                sys.modules[fullname] = module

                # Run the module code.
                exec(bytecode, module.__dict__)
                # Reread the module from sys.modules in case it's changed itself
                module = sys.modules[fullname]

        except Exception:
            # Remove 'fullname' from sys.modules if it was appended there.
            if fullname in sys.modules:
                sys.modules.pop(fullname)
            # TODO Do we need to raise different types of Exceptions for better debugging?
            # PEP302 requires to raise ImportError exception.
            #raise ImportError("Can't load frozen module: %s" % fullname)

            raise

        finally:
            # Release the interpreter's import lock.
            imp_unlock()


        # Module returned only in case of no exception.
        return module

    ### Optional Extensions to the PEP-302 Importer Protocol

    def is_package(self, fullname):
        """
        Return always False since built-in modules are never packages.
        """
        if fullname in self.toc:
            try:
                is_pkg, bytecode = self._pyz_archive.extract(fullname)
                return bool(is_pkg)
            except Exception:
                raise ImportError('Loader FrozenImporter cannot handle module ' + fullname)
        else:
            raise ImportError('Loader FrozenImporter cannot handle module ' + fullname)

    def get_code(self, fullname):
        """
        Get the code object associated with the module.

        ImportError should be raised if module not found.
        """
        if fullname in self.toc:
            try:
                is_pkg, bytecode = self._pyz_archive.extract(fullname)
                return bytecode
            except Exception:
                raise ImportError('Loader FrozenImporter cannot handle module ' + fullname)
        else:
            raise ImportError('Loader FrozenImporter cannot handle module ' + fullname)

    def get_source(self, fullname):
        """
        Method should return the source code for the module as a string.
        But frozen modules does not contain source code.

        Return None.
        """
        if fullname in self.toc:
            return None
        else:
            # ImportError should be raised if module not found.
            raise ImportError('No module named ' + fullname)

    def get_data(self, path):
        """
        This returns the data as a string, or raise IOError if the "file"
        wasn't found. The data is always returned as if "binary" mode was used.

        This method is useful getting resources with 'pkg_resources' that are
        bundled with Python modules in the PYZ archive.

        The 'path' argument is a path that can be constructed by munging
        module.__file__ (or pkg.__path__ items)
        """
        assert path.startswith(SYS_PREFIX + pyi_os_path.os_sep)
        fullname = path[len(SYS_PREFIX)+1:]
        if fullname in self.toc:
            # If the file is in the archive, return this
            return self._pyz_archive.extract(fullname)[1]
        else:
            # Otherwise try to fetch it from the filesystem. Since
            # __file__ attribute works properly just try to open and
            # read it.
            with open(path, 'rb') as fp:
                return fp.read()

    # TODO Do we really need to implement this method?
    def get_filename(self, fullname):
        """
        This method should return the value that __file__ would be set to
        if the named module was loaded. If the module is not found, then
        ImportError should be raised.
        """
        # Then, append the appropriate suffix (__init__.pyc for a package, or just .pyc for a module).
        # Method is_package() will raise ImportError if module not found.
        if self.is_package(fullname):
            filename = pyi_os_path.os_path_join(pyi_os_path.os_path_join(SYS_PREFIX,
                fullname.replace('.', pyi_os_path.os_sep)), '__init__.pyc')
        else:
            filename = pyi_os_path.os_path_join(SYS_PREFIX,
                fullname.replace('.', pyi_os_path.os_sep) + '.pyc')
        return filename


class CExtensionImporter(object):
    """
    PEP-302 hook for sys.meta_path to load Python C extension modules.

    C extension modules are present on the sys.prefix as filenames:

        full.module.name.pyd
        full.module.name.so
        full.module.name.cpython-33m.so
        full.module.name.abi3.so
    """
    def __init__(self):
        # Cache directory content for faster module lookup without
        # file system access.
        files = pyi_os_path.os_listdir(SYS_PREFIX)
        self._file_cache = set(files)

    def find_module(self, fullname, path=None):
        imp_lock()
        module_loader = None  # None means - no module found by this importer.

        # Look in the file list of sys.prefix path (alias PYTHONHOME).
        for ext in EXTENSION_SUFFIXES:
            if fullname + ext in self._file_cache:
                module_loader = self
                break

        imp_unlock()
        return module_loader

    def load_module(self, fullname, path=None):
        imp_lock()

        module = None

        try:
            if sys.version_info[0] == 2:
                # Python 2 implementation - TODO drop or improve it. 'imp' module is no longer built-in.
                # PEP302 If there is an existing module object named 'fullname'
                # in sys.modules, the loader must use that existing module.
                module = sys.modules.get(fullname)

                if module is None:
                    # Need to search for the filename again, since to
                    # be thread-safe we can't store it in find_module().
                    for ext, ext_tuple in EXTENSION_SUFFIXES.iteritems():
                        filename = fullname + ext
                        if filename in self._file_cache:
                            break
                    filename = pyi_os_path.os_path_join(SYS_PREFIX, filename)
                    fp = open(filename, 'rb')
                    module = imp.load_module(fullname, fp, filename, ext_tuple)
                    # Set __file__ attribute.
                    if hasattr(module, '__setattr__'):
                        module.__file__ = filename
                    else:
                        # Some modules (eg: Python for .NET) have no __setattr__
                        # and dict entry have to be set.
                        module.__dict__['__file__'] = filename
            else:
                # PEP302 If there is an existing module object named 'fullname'
                # in sys.modules, the loader must use that existing module.
                module = sys.modules.get(fullname)
                if module is None:
                    # Python 3 implementation.
                    for ext in EXTENSION_SUFFIXES:
                        filename = pyi_os_path.os_path_join(SYS_PREFIX, fullname + ext)
                        # Test if a file exists.
                        # Cannot use os.path.exists. Use workaround with function open().
                        # No exception means that a file exists.
                        try:
                            with open(filename):
                                pass
                        except IOError:
                            # Continue trying new suffix.
                            continue
                        # Load module.
                        loader = EXTENSION_LOADER(fullname, filename)
                        module = loader.load_module(fullname)

        except Exception:
            # Remove 'fullname' from sys.modules if it was appended there.
            if fullname in sys.modules:
                sys.modules.pop(fullname)
            raise  # Raise the same exception again.

        finally:
            # Release the interpreter's import lock.
            imp_unlock()

        return module

    ### Optional Extensions to the PEP302 Importer Protocol

    def is_package(self, fullname):
        """
        Return always False since C extension modules are never packages.
        """
        return False

    def get_code(self, fullname):
        """
        Return None for a C extension module.
        """
        for ext in EXTENSION_SUFFIXES:
            if fullname + ext in self._file_cache:
                return None
        # If module was not found then function still continues.
        # ImportError should be raised if module not found.
        raise ImportError('No module named ' + fullname)

    def get_source(self, fullname):
        """
        Return None for a C extension module.
        """
        # Same implementation as function self.get_code().
        return self.get_code(fullname)

    def get_data(self, path):
        """
        This returns the data as a string, or raise IOError if the "file"
        wasn't found. The data is always returned as if "binary" mode was used.

        The 'path' argument is a path that can be constructed by munging
        module.__file__ (or pkg.__path__ items)
        """
        # Since __file__ attribute works properly just try to open and read it.
        fp = open(path, 'rb')
        content = fp.read()
        fp.close()
        return content

    # TODO Do we really need to implement this method?
    def get_filename(self, fullname):
        """
        This method should return the value that __file__ would be set to
        if the named module was loaded. If the module is not found, then
        ImportError should be raised.
        """
        for ext in EXTENSION_SUFFIXES:
            if fullname + ext in self._file_cache:
                return pyi_os_path.os_path_join(SYS_PREFIX, fullname + ext)
        # ImportError should be raised if module not found.
        raise ImportError('No module named ' + fullname)


def install():
    """
    Install FrozenImporter class and other classes into the import machinery.

    This class method (static method) installs the FrozenImporter class into
    the import machinery of the running process. The importer is added
    to sys.meta_path. It could be added to sys.path_hooks but sys.meta_path
    is processed by Python before looking at sys.path!

    The order of processing import hooks in sys.meta_path:

    1. built-in modules
    2. modules from the bundled ZIP archive
    3. C extension modules
    4. Modules from sys.path
    """
    # Python 3 already has _frozen_importlib.BuiltinImporter on sys.meta_path.
    if sys.version_info[0] == 2:
        # First look in the built-in modules and not bundled ZIP archive.
        sys.meta_path.append(BuiltinImporter())

    # Ensure Python looks in the bundled zip archive for modules before any
    # other places.
    fimp = FrozenImporter()
    sys.meta_path.append(fimp)
    # Add the FrozenImporter to `sys.path_hook`, too, since
    # `pkgutil.get_loader()` does not use `sys.meta_path`. See issue
    # #1689.
    sys.path_hooks.append(fimp)

    # Import hook for the C extension modules.
    sys.meta_path.append(CExtensionImporter())

    if sys.version_info[0] > 2:
        # On Windows there is importer _frozen_importlib.WindowsRegistryFinder that
        # looks for Python modules in Windows registry. The frozen executable should
        # not look for anything in the Windows registry. Remove this importer from
        # sys.meta_path.
        for item in sys.meta_path:
            if hasattr(item, '__name__') and item.__name__ == 'WindowsRegistryFinder':
                sys.meta_path.remove(item)
                break
        # _frozen_importlib.PathFinder is in Python 3 the last importer on sys.meta_path.
        # This importer is also able handle Python C extensions. However, PyInstaller
        # needs own importer to allow extension name 'module.submodle.so'.
        # Add the pathfinder at the end of sys.meta_path.
        pf_idx = 2  # PathFinder is the 3rd in sys.meta_path.
        pf = sys.meta_path.pop(pf_idx)
        sys.meta_path.append(pf)
        # TODO Do we need for Python 3 _frozen_importlib.FrozenImporter? Could it be also removed?
