#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
An Owner does imports from a particular piece of turf
That is, there's an Owner for each thing on sys.path
There are owners for directories and .pyz files.
There could be owners for zip files, or even URLs.
Note that they replace the string in sys.path,
but str(sys.path[n]) should yield the original string.
"""


import imp
import marshal
import os

from PyInstaller import depend
from PyInstaller.compat import PYCO, caseOk
from PyInstaller.loader import pyi_archive


import PyInstaller.log as logging
logger = logging.getLogger('PyInstaller.build.mf')


class OwnerError(Exception):
    pass


class Owner:
    """
    Base class for loading Python bytecode from different places.
    """
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return self.path

    def getmod(self, nm):
        return None


class BaseDirOwner(Owner):
    """
    Base class for loading bytecode of Python modules from file system.
    """
    def _getsuffixes(self):
        return imp.get_suffixes()

    def getmod(self, nm, getsuffixes=None, loadco=marshal.loads):
        if getsuffixes is None:
            getsuffixes = self._getsuffixes
        possibles = [(nm, 0, None)]
        if self._isdir(nm) and self._caseok(nm):
            possibles.insert(0, (os.path.join(nm, '__init__'), 1, nm))
        py = pyc = None
        for pth, ispkg, pkgpth in possibles:
            for ext, mode, typ in getsuffixes():
                attempt = pth + ext
                modtime = self._modtime(attempt)
                if modtime is not None:
                    # Check case
                    if not self._caseok(attempt):
                        continue
                    if typ == imp.C_EXTENSION:
                        #logger.debug("%s.getmod -> ExtensionModule(%s, %s)", self.__class__.__name__, nm, attempt)
                        return depend.modules.ExtensionModule(nm, os.path.join(self.path, attempt))
                    elif typ == imp.PY_SOURCE:
                        py = (attempt, modtime)
                    else:
                        pyc = (attempt, modtime)
            if py or pyc:
                break
        if py is None and pyc is None:
            #logger.debug("%s.getmod -> (py == pyc == None)", self.__class__.__name__)
            return None

        co = None
        ## if nm == 'archive':
        ##     import pdb ; pdb.set_trace()
        if pyc:
            stuff = self._read(pyc[0])
            # If this file was not generated for this version of
            # Python, we need to regenerate it.
            if stuff[:4] != imp.get_magic():
                logger.warn("wrong version .py%s found (%s), will use .py",
                            PYCO, pyc[0])
            else:
                try:
                    co = loadco(stuff[8:])
                    pth = pyc[0]
                except (ValueError, EOFError):
                    pyc = None
                    logger.warn("bad .py%s found (%s), will use .py",
                                PYCO, pyc[0])

        if co is None or py and pyc[1] < py[1]:
            # If we have no pyc or py is newer
            try:
                stuff = self._read(py[0]) + '\n'
                co = compile(stuff.replace("\r\n", "\n"), py[0], 'exec')
                pth = py[0] + PYCO
                logger.debug("compiled %s", pth)
            except SyntaxError, e:
                logger.exception(e)
                raise SystemExit(10)

        if co is None:
            #logger.debug("%s.getmod -> None", self.__class__.__name__)
            return None

        pth = os.path.join(self.path, pth)
        if not os.path.isabs(pth):
            pth = os.path.abspath(pth)
        if ispkg:
            mod = self._pkgclass()(nm, pth, co)
        else:
            mod = self._modclass()(nm, pth, co)
        #logger.debug("%s.getmod -> %s", self.__class__.__name__, mod)
        return mod


class DirOwner(BaseDirOwner):

    def __init__(self, path):
        if path == '':
            path = os.getcwd()
        if not os.path.isdir(path):
            raise OwnerError("%s is not a directory" % repr(path))
        Owner.__init__(self, path)

    def _isdir(self, fn):
        return os.path.isdir(os.path.join(self.path, fn))

    def _modtime(self, fn):
        try:
            return os.stat(os.path.join(self.path, fn))[8]
        except OSError:
            return None

    def _read(self, fn):
        return open(os.path.join(self.path, fn), 'rb').read()

    def _pkgclass(self):
        return depend.modules.PkgModule

    def _modclass(self):
        return depend.modules.PyModule

    def _caseok(self, fn):
        return caseOk(os.path.join(self.path, fn))


class ZipOwner(BaseDirOwner):
    """
    Load bytecode of Python modules from .egg files.

    zipimporter cannot be used here because it has a stupid bug:

      >>> z.find_module("setuptools.setuptools.setuptools.setuptools.setuptools") is not None
      True

    So mf will go into infinite recursion. Instead, we'll reuse
    the BaseDirOwner logic, simply changing the template methods.
    """
    def __init__(self, path):
        import zipfile
        try:
            self.zf = zipfile.ZipFile(path, "r")
        except IOError:
            raise OwnerError("%s is not a zipfile" % path)
        Owner.__init__(self, path)

    def getmod(self, fn):
        fn = fn.replace(".", "/")
        return BaseDirOwner.getmod(self, fn)

    def _modtime(self, fn):
        # zipfiles always use forward slashes
        fn = fn.replace("\\", "/")
        try:
            dt = self.zf.getinfo(fn).date_time
            return dt
        except KeyError:
            return None

    def _isdir(self, fn):
        # No way to find out if "fn" is a directory
        # so just always look into it in case it is.
        return True

    def _caseok(self, fn):
        # zipfile is always case-sensitive, so surely
        # there is no case mismatch.
        return True

    def _read(self, fn):
        # zipfiles always use forward slashes
        fn = fn.replace("\\", "/")
        return self.zf.read(fn)

    def _pkgclass(self):
        return lambda *args: depend.modules.PkgInZipModule(self, *args)

    def _modclass(self):
        return lambda *args: depend.modules.PyInZipModule(self, *args)


class PYZOwner(Owner):
    """
    Class for loading bytecode of Python modules from PYZ files.

    PYZ file is internal PyInstaller format embedded into final executable.

    It is possible to have a custom .spec file which packs a subset of Python
    files into a PYZ file, and then drop it on the disk somewhere. When the PYZ
    file is added to sys.path, PYZOwner will parse it and make the modules
    within it available at import time.

    NOTE: PYZ format cannot be replaced by zipimport module.

    The problem is that we have no control over zipimport; for instance,
    it doesn't work if the zip file is embedded into a PKG appended
    to an executable, like we create in one-file.
    """
    def __init__(self, path):
        self.pyz = pyi_archive.ZlibArchive(path)
        Owner.__init__(self, path)

    def getmod(self, nm):
        rslt = self.pyz.extract(nm)
        if not rslt:
            return None
        ispkg, co = rslt
        if ispkg:
            return depend.modules.PkgInPYZModule(nm, co, self)
        return depend.modules.PyModule(nm, self.path, co)
