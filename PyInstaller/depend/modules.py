#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
All we're doing here is tracking, not importing
If we were importing, these would be hooked to the real module objects
"""


import os
import pkgutil

from PyInstaller.compat import ctypes, PYCO
from PyInstaller.depend.utils import _resolveCtypesImports, scan_code

import PyInstaller.depend.impdirector


class Module:
    _ispkg = 0
    typ = 'UNKNOWN'

    def __init__(self, nm):
        self.__name__ = nm
        self.__file__ = None
        self._all = []
        self.pyinstaller_imports = []
        self.pyinstaller_warnings = []
        self.pyinstaller_binaries = []
        self.pyinstaller_datas = []
        self._xref = {}

    def ispackage(self):
        return self._ispkg

    def doimport(self, nm):
        pass

    def xref(self, nm):
        self._xref[nm] = 1

    def __str__(self):
        return ("<%s %r %s imports=%s binaries=%s datas=%s>" %
                (self.__class__.__name__, self.__name__, self.__file__,
                 self.pyinstaller_imports, self.pyinstaller_binaries, self.pyinstaller_datas))


class BuiltinModule(Module):
    typ = 'BUILTIN'

    def __init__(self, nm):
        Module.__init__(self, nm)


class ExtensionModule(Module):
    typ = 'EXTENSION'

    def __init__(self, nm, pth):
        Module.__init__(self, nm)
        self.__file__ = pth


class PyModule(Module):
    typ = 'PYMODULE'

    def __init__(self, nm, pth, co):
        Module.__init__(self, nm)
        self.co = co
        self.__file__ = pth
        if os.path.splitext(self.__file__)[1] == '.py':
            self.__file__ = self.__file__ + PYCO
        self.scancode()

    def _remove_duplicate_entries(self, item_list):
        """
        Remove duplicate entries from the list.
        """
        # The strategy is to convert a list to a set and then back.
        # This conversion will eliminate duplicate entries.
        return list(set(item_list))

    def scancode(self):
        self.pyinstaller_imports, self.pyinstaller_warnings, self.pyinstaller_binaries, allnms = scan_code(self.co)
        self.pyinstaller_imports = self._remove_duplicate_entries(self.pyinstaller_imports)

        if allnms:
            self._all = allnms
        if ctypes and self.pyinstaller_binaries:
            self.pyinstaller_binaries = _resolveCtypesImports(self.pyinstaller_binaries)
            # Just to make sure there will be no duplicate entries.
            self.pyinstaller_binaries = self._remove_duplicate_entries(self.pyinstaller_binaries)


class PyScript(PyModule):
    typ = 'PYSOURCE'

    def __init__(self, pth, co):
        Module.__init__(self, '__main__')
        self.co = co
        self.__file__ = pth
        self.scancode()


class PkgModule(PyModule):
    typ = 'PYMODULE'

    def __init__(self, nm, pth, co):
        PyModule.__init__(self, nm, pth, co)
        self._ispkg = 1
        pth = os.path.dirname(pth)
        self.__path__ = [pth]
        self._update_director(force=True)

    def _update_director(self, force=False):
        if force or self.subimporter.path != self.__path__:
            self.subimporter = PyInstaller.depend.impdirector.PathImportDirector(self.__path__)

    def doimport(self, nm):
        self._update_director()
        mod = self.subimporter.getmod(nm)
        if mod:
            mod.__name__ = self.__name__ + '.' + mod.__name__
        return mod


class NamespaceModule(PkgModule):
    typ = 'NAMESPACE'
    _ispkg = 1

    def __init__(self, nm, pth):
        fnm = os.path.join(pth[0], '__init__.py')
        co = compile('', fnm, 'exec')
        PkgModule.__init__(self, nm, fnm, co)
        self.__path__ = pth
        self._update_director(force=True)

    def doimport(self, nm):
        fqname = self.__name__ + '.' + nm
        self.__path__ = pkgutil.extend_path(self.__path__, fqname)
        self._update_director(force=True)
        m =  PkgModule.doimport(self, nm)
        return m


class PkgInPYZModule(PyModule):
    def __init__(self, nm, co, pyzowner):
        PyModule.__init__(self, nm, co.co_filename, co)
        self._ispkg = 1
        self.__path__ = [str(pyzowner)]
        self.owner = pyzowner

    def doimport(self, nm):
        mod = self.owner.getmod(self.__name__ + '.' + nm)
        return mod


class PyInZipModule(PyModule):
    typ = 'ZIPFILE'

    def __init__(self, zipowner, nm, pth, co):
        PyModule.__init__(self, nm, co.co_filename, co)
        self.owner = zipowner


class PkgInZipModule(PyModule):
    typ = 'ZIPFILE'

    def __init__(self, zipowner, nm, pth, co):
        PyModule.__init__(self, nm, co.co_filename, co)
        self._ispkg = 1
        self.__path__ = [str(zipowner)]
        self.owner = zipowner

    def doimport(self, nm):
        mod = self.owner.getmod(self.__name__ + '.' + nm)
        return mod
