#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
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


### **NOTE** This module is used during bootstrap.
### Import *ONLY* builtin modules.
### List of built-in modules: sys.builtin_module_names


import sys
import _frozen_importlib

import pyimod01_os_path as pyi_os_path
from pyimod02_archive import ArchiveReadError, ZlibArchiveReader

SYS_PREFIX = sys._MEIPASS
SYS_PREFIXLEN = len(SYS_PREFIX)

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


class FrozenImporter(object):
    """
    Load bytecode of Python modules from the executable created by PyInstaller.

    Python bytecode is zipped and appended to the executable.

    NOTE: PYZ format cannot be replaced by zipimport module.

    The problem is that we have no control over zipimport; for instance,
    it doesn't work if the zip file is embedded into a PKG appended
    to an executable, like we create in one-file.

    This used to be PEP-302 finder and loader class for the ``sys.meta_path``
    hook. A PEP-302 finder requires method find_module() to return loader class
    with method load_module(). However, both of these methods were deprecated
    in python 3.4 by PEP-451 (see below). Therefore, this class now provides
    only optional extensions to the PEP-302 importer protocol.

    This is also a PEP-451 finder and loader class for the ModuleSpec type
    import system. A PEP-451 finder requires method find_spec(), a PEP-451
    loader requires methods exec_module(), load_module() and (optionally)
    create_module(). All these methods are implemented in this one class.

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
        # sys.path does not contain filename of executable with bundled zip archive.
        # Raise import error.
        raise ImportError("Can't load frozen modules.")

    # Private helper
    def _is_pep420_namespace_package(self, fullname):
        if fullname in self.toc:
            try:
                return self._pyz_archive.is_pep420_namespace_package(fullname)
            except Exception as e:
                raise ImportError(
                    'Loader FrozenImporter cannot handle module ' + fullname
                ) from e
        else:
            raise ImportError('Loader FrozenImporter cannot handle module ' + fullname)

    ### Optional Extensions to the PEP-302 Importer Protocol

    def is_package(self, fullname):
        if fullname in self.toc:
            try:
                return self._pyz_archive.is_package(fullname)
            except Exception as e:
                raise ImportError(
                    'Loader FrozenImporter cannot handle module ' + fullname
                ) from e
        else:
            raise ImportError('Loader FrozenImporter cannot handle module ' + fullname)

    def get_code(self, fullname):
        """
        Get the code object associated with the module.

        ImportError should be raised if module not found.
        """
        try:
            # extract() returns None if fullname not in the archive, thus the
            # next line will raise an execpion which will be catched just
            # below and raise the ImportError.
            return self._pyz_archive.extract(fullname)[1]
        except Exception as e:
            raise ImportError(
                'Loader FrozenImporter cannot handle module ' + fullname
            ) from e

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
        fullname = path[SYS_PREFIXLEN+1:]
        if fullname in self.toc:
            # If the file is in the archive, return this
            return self._pyz_archive.extract(fullname)[1]
        else:
            # Otherwise try to fetch it from the filesystem. Since
            # __file__ attribute works properly just try to open and
            # read it.
            with open(path, 'rb') as fp:
                return fp.read()

    def get_filename(self, fullname):
        """
        This method should return the value that __file__ would be set to
        if the named module was loaded. If the module is not found, then
        ImportError should be raised.
        """
        # The absolute absolute path to the executable is taken from
        # sys.prefix. In onefile mode it points to the temp directory where
        # files are unpacked by PyInstaller. Then, append the appropriate
        # suffix (__init__.pyc for a package, or just .pyc for a module).
        # Method is_package() will raise ImportError if module not found.
        if self.is_package(fullname):
            filename = pyi_os_path.os_path_join(pyi_os_path.os_path_join(SYS_PREFIX,
                fullname.replace('.', pyi_os_path.os_sep)), '__init__.pyc')
        else:
            filename = pyi_os_path.os_path_join(SYS_PREFIX,
                fullname.replace('.', pyi_os_path.os_sep) + '.pyc')
        return filename

    def find_spec(self, fullname, path=None, target=None):
        """
        PEP-451 finder.find_spec() method for the ``sys.meta_path`` hook.

        fullname     fully qualified name of the module
        path         None for a top-level module, or package.__path__ for
                     submodules or subpackages.
        target       unused by this Finder

        Finders are still responsible for identifying, and typically creating,
        the loader that should be used to load a module. That loader will now
        be stored in the module spec returned by find_spec() rather than
        returned directly. As is currently the case without the PEP-452, if a
        loader would be costly to create, that loader can be designed to defer
        the cost until later.

        Finders must return ModuleSpec objects when find_spec() is called.
        This new method replaces find_module() and find_loader() (in the
        PathEntryFinder case). If a loader does not have find_spec(),
        find_module() and find_loader() are used instead, for
        backward-compatibility.
        """
        entry_name = None  # None means - no module found in this importer.

        if fullname in self.toc:
            entry_name = fullname
            trace("import %s # PyInstaller PYZ", fullname)
        elif path is not None:
            # Try to handle module.__path__ modifications by the modules themselves
            # Reverse the fake __path__ we added to the package module to a
            # dotted module name and add the tail module from fullname onto that
            # to synthesize a new fullname
            modname = fullname.rsplit('.')[-1]

            for p in path:
                p = p[SYS_PREFIXLEN+1:]
                parts = p.split(pyi_os_path.os_sep)
                if not parts: continue
                if not parts[0]:
                    parts = parts[1:]
                parts.append(modname)
                entry_name = ".".join(parts)
                if entry_name in self.toc:
                    trace("import %s as %s # PyInstaller PYZ (__path__ override: %s)",
                          entry_name, fullname, p)
                    break
            else:
                entry_name = None

        if entry_name is None:
            trace("# %s not found in PYZ", fullname)
            return None

        if self._is_pep420_namespace_package(entry_name):
            # PEP-420 namespace package; as per PEP 451, we need to
            # return a spec with "loader" set to None (a.k.a. not set)
            spec = _frozen_importlib.ModuleSpec(
                fullname, None,
                is_package=True)
            return spec

        # origin has to be the filename
        origin = self.get_filename(entry_name)
        is_pkg = self.is_package(entry_name)

        spec =  _frozen_importlib.ModuleSpec(
            fullname, self,
            is_package=is_pkg, origin=origin,
            # Provide the entry_name for the loader to use during loading
            loader_state = entry_name)

        # Make the import machinery set __file__.
        # PEP 451 says: "has_location" is true if the module is locatable. In
        # that case the spec's origin is used as the location and __file__ is
        # set to spec.origin. If additional location information is required
        # (e.g. zipimport), that information may be stored in
        # spec.loader_state.
        spec.has_location = True
        return spec

    def create_module(self, spec):
        """
        PEP-451 loader.create_module() method for the ``sys.meta_path`` hook.

        Loaders may also implement create_module() that will return a new
        module to exec. It may return None to indicate that the default module
        creation code should be used. One use case, though atypical, for
        create_module() is to provide a module that is a subclass of the
        builtin module type. Most loaders will not need to implement
        create_module(),

        create_module() should properly handle the case where it is called
        more than once for the same spec/module. This may include returning
        None or raising ImportError.
        """
        # Opposed to what is defined in PEP-451, this method is not optional.
        # We want the default results, so we simply return None (which is
        # handled for su my the import machinery). See
        # https://bugs.python.org/issue23014 for more information.
        return None

    def exec_module(self, module):
        """
        PEP-451 loader.exec_module() method for the ``sys.meta_path`` hook.

        Loaders will have a new method, exec_module(). Its only job is to
        "exec" the module and consequently populate the module's namespace. It
        is not responsible for creating or preparing the module object, nor
        for any cleanup afterward. It has no return value. exec_module() will
        be used during both loading and reloading.

        exec_module() should properly handle the case where it is called more
        than once. For some kinds of modules this may mean raising ImportError
        every time after the first time the method is called. This is
        particularly relevant for reloading, where some kinds of modules do
        not support in-place reloading.
        """
        spec = module.__spec__
        bytecode = self.get_code(spec.loader_state)

        # Set by the import machinery
        assert hasattr(module, '__file__')

        # If `submodule_search_locations` is not None, this is a package;
        # set __path__.
        if spec.submodule_search_locations is not None:
            # Since PYTHONHOME is set in bootloader, 'sys.prefix' points to
            # the correct path where PyInstaller should find bundled dynamic
            # libraries. In one-file mode it points to the tmp directory where
            # bundled files are extracted at execution time.
            #
            # __path__ cannot be empty list because 'wx' module prepends
            # something to it. It cannot contain value 'sys.prefix' because
            # 'xml.etree.cElementTree' fails otherwise.
            #
            # Set __path__ to point to 'sys.prefix/package/subpackage'.
            module.__path__ = [pyi_os_path.os_path_dirname(module.__file__)]

        exec(bytecode, module.__dict__)


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
    # Ensure Python looks in the bundled zip archive for modules before any
    # other places.
    fimp = FrozenImporter()
    sys.meta_path.append(fimp)

    # On Windows there is importer _frozen_importlib.WindowsRegistryFinder that
    # looks for Python modules in Windows registry. The frozen executable should
    # not look for anything in the Windows registry. Remove this importer from
    # sys.meta_path.
    for item in sys.meta_path:
        if hasattr(item, '__name__') and item.__name__ == 'WindowsRegistryFinder':
            sys.meta_path.remove(item)
            break
    # _frozen_importlib.PathFinder is also able to handle Python C
    # extensions. However, PyInstaller needs its own importer since it
    # uses extension names like 'module.submodle.so' (instead of paths).
    # As of Python 3.7.0b2, there are several PathFinder instances (and
    # duplicate ones) on sys.meta_path. This propobly is a bug, see
    # https://bugs.python.org/issue33128. Thus we need to move all of them
    # to the end, eliminating duplicates .
    pathFinders = []
    for item in reversed(sys.meta_path):
        if getattr(item, '__name__', None) == 'PathFinder':
            sys.meta_path.remove(item)
            if not item in pathFinders:
                pathFinders.append(item)
    sys.meta_path.extend(reversed(pathFinders))
    # TODO Do we need for Python 3 _frozen_importlib.FrozenImporter? Could it be also removed?
