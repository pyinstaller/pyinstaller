#
# Copyright (C) 2005, Giovanni Bajo
#
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA


# All we're doing here is tracking, not importing
# If we were importing, these would be hooked to the real module objects


import os

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
        self.imports = []
        self.warnings = []
        self.binaries = []
        self.datas = []
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
                 self.imports, self.binaries, self.datas))


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

    def scancode(self):
        self.imports, self.warnings, self.binaries, allnms = scan_code(self.co)
        if allnms:
            self._all = allnms
        if ctypes and self.binaries:
            self.binaries = _resolveCtypesImports(self.binaries)


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
