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


import sys

from pyi_archive import ZlibArchive


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
    def __init__(self, pyz_filepath):
        """
        Load, unzip and initialize the Zip archive bundled with the executable.
        """
        try:
            # Unzip zip archive bundled with the executable.
            self._pyz_archive = ZlibArchive(pyz_filepath)
            # Verify the integrity of the zip archive with Python modules.
            self._pyz_archive.checkmagic()
        except (IOError, ArchiveReadError) as e:
            # TODO handle properly exeptions. What exeption should be raised at this place according to PEP302?
            raise Exception
            
    def find_module(self, fullname, path=None):
        """
        PEP-302 finder.find_module() method for the ``sys.meta_path`` hook.

        fullname     fully qualified name of the module
        path         None for a top-level module, or package.__path__ for submodules or subpackages.

        Return a loader object if the module was found, or None if it wasn't. If find_module() raises
        an exception, it will be propagated to the caller, aborting the import.
        """
        # TODO rewrite this method.
        #print >> sys.stderr, "find_module (%s): %r" % (self.dir, fullname), 
        acquire_lock()
        try:
            dir = self.dir
            try:
                files = sys.quickimport_cache[dir]
            except Exception, e:
                raise ImportError("Can't import %r: No quickimport dir cache for dir %r: %s" % (fullname, dir, e) )
            basename = fullname.rsplit('.', 1)[-1]
            basenameNormcase = os.path.normcase(basename)
            if not basenameNormcase in files:
                for s in suffixes:
                    if (basenameNormcase + s) in files:
                        break
                else:
                    #print >> sys.stderr, ""
                    return None
            # this path is a candidate
            importer = sys.path_importer_cache.get(dir)
            assert importer is self
            try:
                #print >> sys.stderr, "testing.. ",
                loader = ImpLoader(fullname, *find_module(basename, [dir]))
                #print >> sys.stderr, "found"
                return loader
            except ImportError, e:
                #print >> sys.stderr, e
                return None
        finally:
            release_lock()

    def load_module(self, fullname, path=None):
        """
        PEP-302 loader.load_module() method for the ``sys.meta_path`` hook.
        """
        # TODO rewrite this method.


def install(self):
    """
    Install FrozenImporter class and other classes into the import machinery.

    This class method (static method) installs the FrozenImporter class into
    the import machinery of the running process. The importer is added
    to sys.meta_path. It could be added to sys.path_hooks but sys.meta_path
    is processed by Python before looking at sys.path!
    """
    # TODO how to get path to ZIP archive bundled in the executable?
    pyz_path = None
    # Ensure Python looks first in the bundled zip archive for modules.
    sys.meta_path.append(FrozenImporter(pyz_path))
