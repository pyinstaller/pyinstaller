#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
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


import imp
import sys
import pyi_os_path

from pyi_archive import ArchiveReadError, ZlibArchive


class BuiltinImporter(object):
    """
    PEP-302 wrapper of the built-in modules for sys.meta_path.

    This wrapper ensures that import machinery will not look for built-in
    modules in the bundled ZIP archive.
    """
    def find_module(self, fullname, path=None):
        imp.acquire_lock()
        module_loader = None  # None means - no module found by this importer.

        # Look in the list of built-in modules.
        if fullname in sys.builtin_module_names:
            module_loader = self

        imp.release_lock()
        return module_loader

    def load_module(self, fullname, path=None):
        imp.acquire_lock()

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
            # Release the interpreter's import lock.
            imp.release_lock()
            raise  # Raise the same exception again.

        # Release the interpreter's import lock.
        imp.release_lock()

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
        # for the ZlibArchive class and remove this item from sys.path.
        # It was needed only for FrozenImporter class. Wrong path from sys.path
        # Raises ArchiveReadError exception.
        for pyz_filepath in sys.path:
            try:
                # Unzip zip archive bundled with the executable.
                self._pyz_archive = ZlibArchive(pyz_filepath)
                # Verify the integrity of the zip archive with Python modules.
                self._pyz_archive.checkmagic()
                # End this method since no Exception was raised we can assume
                # ZlibArchive was successfully loaded. Let's remove 'pyz_filepath'
                # from sys.path.
                sys.path.remove(pyz_filepath)
                # Some runtime hook might need access to the list of available
                # frozen module. Let's make them accessible as a set().
                self.toc = set(self._pyz_archive.toc.keys())
                # Return - no error was raised.
                return
            except IOError:
                # Item from sys.path is not ZlibArchive let's try next.
                continue
            except ArchiveReadError:
                # Item from sys.path is not ZlibArchive let's try next.
                continue
        # sys.path does not contain filename of executable with bundled zip archive.
        # Raise import error.
        raise ImportError("Can't load frozen modules.")

    def find_module(self, fullname, path=None):
        """
        PEP-302 finder.find_module() method for the ``sys.meta_path`` hook.

        fullname     fully qualified name of the module
        path         None for a top-level module, or package.__path__ for submodules or subpackages.

        Return a loader object if the module was found, or None if it wasn't. If find_module() raises
        an exception, it will be propagated to the caller, aborting the import.
        """
        # Acquire the interpreter's import lock for the current thread. Tis
        # lock should be used by import hooks to ensure thread-safety when
        # importing modules.
        imp.acquire_lock()
        module_loader = None  # None means - no module found in this importer.

        if fullname in self.toc:
            # Tell the import machinery to use self.load_module() to load the module.
            module_loader = self

        # Release the interpreter's import lock.
        imp.release_lock()

        return module_loader

    def load_module(self, fullname, path=None):
        """
        PEP-302 loader.load_module() method for the ``sys.meta_path`` hook.

        Return the loaded module (instance of imp.new_module()) or raises
        an exception, preferably ImportError if an existing exception
        is not being propagated.
        """
        # Acquire the interpreter's import lock.
        imp.acquire_lock()
        module = None
        try:
            # PEP302 If there is an existing module object named 'fullname'
            # in sys.modules, the loader must use that existing module.
            module = sys.modules.get(fullname)

            # Module not in sys.modules - load it and it to sys.modules.
            if module is None:
                # Load code object from the bundled ZIP archive.
                is_pkg, bytecode = self._pyz_archive.extract(fullname)
                # Create new empty 'module' object.
                module = imp.new_module(fullname)

                # TODO Replace bytecode.co_filename by something more meaningful:
                # e.g. /absolute/path/frozen_executable/path/to/module/module_name.pyc
                # Paths from developer machine are masked.

                ### Set __file__ attribute of a module relative to the executable
                # so that data files can be found. The absolute absolute path
                # to the executable is taken from sys.prefix. In onefile mode it
                # points to the temp directory where files are unpacked by PyInstaller.
                abspath = sys.prefix
                # Then, append the appropriate suffix (__init__.pyc for a package, or just .pyc for a module).
                if is_pkg:
                    module.__file__ = pyi_os_path.os_path_join(pyi_os_path.os_path_join(abspath,
                        fullname.replace('.', pyi_os_path.os_sep)), '__init__.pyc')
                else:
                    module.__file__ = pyi_os_path.os_path_join(abspath,
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

                ### Add module object to sys.modules dictionary.
                # Module object must be in sys.modules before the loader
                # executes the module code. This is crucial because the module
                # code may (directly or indirectly) import itself; adding it
                # to sys.modules beforehand prevents unbounded recursion in the
                # worst case and multiple loading in the best.
                sys.modules[fullname] = module

                # Run the module code.
                exec(bytecode, module.__dict__)

        except Exception:
            # Remove 'fullname' from sys.modules if it was appended there.
            if fullname in sys.modules:
                sys.modules.pop(fullname)
            # TODO Do we need to raise different types of Exceptions for better debugging?
            # PEP302 requires to raise ImportError exception.
            #raise ImportError("Can't load frozen module: %s" % fullname)

            # Release the interpreter's import lock.
            imp.release_lock()
            raise

        # Release the interpreter's import lock.
        imp.release_lock()

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
                return is_pkg
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
        abspath = sys.prefix
        # Then, append the appropriate suffix (__init__.pyc for a package, or just .pyc for a module).
        # Method is_package() will raise ImportError if module not found.
        if self.is_package(fullname):
            filename = pyi_os_path.os_path_join(pyi_os_path.os_path_join(abspath,
                fullname.replace('.', pyi_os_path.os_sep)), '__init__.pyc')
        else:
            filename = pyi_os_path.os_path_join(abspath,
                fullname.replace('.', pyi_os_path.os_sep) + '.pyc')
        return filename


class CExtensionImporter(object):
    """
    PEP-302 hook for sys.meta_path to load Python C extension modules.

    C extension modules are present on the sys.prefix as filenames:

        full.module.name.pyd
        full.module.name.so
    """
    def __init__(self):
        # TODO cache directory content for faster module lookup without file system access.
        # Create hashmap of directory content for better performance.
        files = pyi_os_path.os_listdir(sys.prefix)
        self._file_cache = set(files)

        self._suffixes = dict()

        # Find the platform specific suffixes. On Windows it is .pyd, on Linux/Unix .so.
        for ext, mode, typ in imp.get_suffixes():
            if typ == imp.C_EXTENSION:
                self._suffixes[ext] = (ext, mode, typ)

    def find_module(self, fullname, path=None):
        imp.acquire_lock()
        module_loader = None  # None means - no module found by this importer.

        # Look in the file list of sys.prefix path (alias PYTHONHOME).
        for ext, c_ext_tuple in self._suffixes.items():
            if fullname + ext in self._file_cache:
                self._c_ext_tuple = c_ext_tuple
                self._suffix = ext
                module_loader = self
                break

        imp.release_lock()
        return module_loader

    def load_module(self, fullname, path=None):
        imp.acquire_lock()

        try:
            # PEP302 If there is an existing module object named 'fullname'
            # in sys.modules, the loader must use that existing module.
            module = sys.modules.get(fullname)

            if module is None:
                filename = pyi_os_path.os_path_join(sys.prefix, fullname + self._suffix)
                fp = open(filename, 'rb')
                module = imp.load_module(fullname, fp, filename, self._c_ext_tuple)
                # Set __file__ attribute.
                if hasattr(module, '__setattr__'):
                    module.__file__ = filename
                else:
                    # Some modules (eg: Python for .NET) have no __setattr__
                    # and dict entry have to be set.
                    module.__dict__['__file__'] = filename

        except Exception:
            # Remove 'fullname' from sys.modules if it was appended there.
            if fullname in sys.modules:
                sys.modules.pop(fullname)
            # Release the interpreter's import lock.
            imp.release_lock()
            raise  # Raise the same exception again.

        # Release the interpreter's import lock.
        imp.release_lock()

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
        if fullname + self._suffix in self._file_cache:
            return None
        else:
            # ImportError should be raised if module not found.
            raise ImportError('No module named ' + fullname)

    def get_source(self, fullname):
        """
        Return None for a C extension module.
        """
        if fullname + self._suffix in self._file_cache:
            return None
        else:
            # ImportError should be raised if module not found.
            raise ImportError('No module named ' + fullname)

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
        if fullname + self._suffix in self._file_cache:
            return pyi_os_path.os_path_join(sys.prefix, fullname + self._suffix)
        else:
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
    """
    # First look in the built-in modules and not bundled ZIP archive.
    sys.meta_path.append(BuiltinImporter())
    # Ensure Python looks in the bundled zip archive for modules before any
    # other places.
    sys.meta_path.append(FrozenImporter())
    # Import hook for the C extension modules.
    sys.meta_path.append(CExtensionImporter())
