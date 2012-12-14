#
# Copyright (C) 2012, Martin Zibricky
# Copyright (C) 2005-2011, Giovanni Bajo
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


### **NOTE** This module is used during bootstrap.
### Import *ONLY* builtin modules.
### List of built-in modules: sys.builtin_module_names


import imp
import sys

from pyi_archive import ArchiveReadError, ZlibArchive


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
                return
            except (IOError, ArchiveReadError) as e:
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
        # TODO rewrite this method.
        module_loader = None  # None means - no module found in this importer.
        try:
            print fullname

            if fullname in self._pyz_archive.toc:
                print '... found'
                # Tell the import machinery to use self.load_module() to load the module.
                module_loader = self  
            else:
                print '... found'
        finally:
            # Release the interpreter's import lock.
            imp.release_lock()
        return module_loader

    def load_module(self, fullname, path=None):
        """
        PEP-302 loader.load_module() method for the ``sys.meta_path`` hook.
        """
        # TODO rewrite this method.


def install():
    """
    Install FrozenImporter class and other classes into the import machinery.

    This class method (static method) installs the FrozenImporter class into
    the import machinery of the running process. The importer is added
    to sys.meta_path. It could be added to sys.path_hooks but sys.meta_path
    is processed by Python before looking at sys.path!
    """
    # Ensure Python looks first in the bundled zip archive for modules.
    sys.meta_path.append(FrozenImporter())
