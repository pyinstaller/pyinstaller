#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
ImportDirectors live on the metapath.
There's one for builtins and one for sys.path.
Windows gets one for modules gotten from the Registry
There should be one for Frozen modules
Mac would have them for PY_RESOURCE modules etc.
A generalization of Owner - their concept of "turf" is broader
"""


import os
import sys
import imp
import marshal

from PyInstaller import depend


import PyInstaller.depend.owner
import PyInstaller.log as logging


logger = logging.getLogger(__name__)


def getDescr(fnm):
    ext = os.path.splitext(fnm)[1]
    for (suffix, mode, typ) in imp.get_suffixes():
        if suffix == ext:
            return (suffix, mode, typ)


class ImportDirector(PyInstaller.depend.owner.Owner):
    pass


class BuiltinImportDirector(ImportDirector):
    def __init__(self):
        self.path = 'Builtins'

    def getmod(self, nm, isbuiltin=imp.is_builtin):
        if isbuiltin(nm):
            return depend.modules.BuiltinModule(nm)
        return None


class RegistryImportDirector(ImportDirector):
    # for Windows only
    def __init__(self):
        self.path = "WindowsRegistry"
        self.map = {}
        try:
            import win32api
            import win32con
        except ImportError:
            return

        subkey = r"Software\Python\PythonCore\%s\Modules" % sys.winver
        for root in (win32con.HKEY_CURRENT_USER, win32con.HKEY_LOCAL_MACHINE):
            try:
                hkey = win32api.RegOpenKeyEx(root, subkey, 0, win32con.KEY_READ)
            except Exception, e:
                logger.debug('RegistryImportDirector: %s' % e)
                continue

            numsubkeys, numvalues, lastmodified = win32api.RegQueryInfoKey(hkey)
            for i in range(numsubkeys):
                subkeyname = win32api.RegEnumKey(hkey, i)
                hskey = win32api.RegOpenKeyEx(hkey, subkeyname, 0, win32con.KEY_READ)
                val = win32api.RegQueryValueEx(hskey, '')
                desc = getDescr(val[0])
                #print " RegistryImportDirector got %s %s" % (val[0], desc)  #XXX
                self.map[subkeyname] = (val[0], desc)
                hskey.Close()
            hkey.Close()
            break

    def getmod(self, nm, loadco=marshal.loads):
        stuff = self.map.get(nm)
        if stuff:
            fnm, (suffix, mode, typ) = stuff
            if typ == imp.C_EXTENSION:
                return depend.modules.ExtensionModule(nm, fnm)
            elif typ == imp.PY_SOURCE:
                try:
                    stuff = open(fnm, 'rU').read() + '\n'
                    co = compile(stuff, fnm, 'exec')
                except SyntaxError, e:
                    logger.exception(e)
                    raise SystemExit(10)
            else:
                stuff = open(fnm, 'rb').read()
                co = loadco(stuff[8:])
            return depend.modules.PyModule(nm, fnm, co)
        return None


class PathImportDirector(ImportDirector):
    def __init__(self, pathlist=None, importers=None):
        if pathlist is None:
            self.path = sys.path
        else:
            self.path = pathlist

        self.ownertypes = filter(None, [
            PyInstaller.depend.owner.DirOwner,
            PyInstaller.depend.owner.ZipOwner,
            PyInstaller.depend.owner.PYZOwner,
            PyInstaller.depend.owner.Owner,
        ])

        if importers:
            self.shadowpath = importers
        else:
            self.shadowpath = {}
        self.building = set()

    def __str__(self):
        return str(self.path)

    def getmod(self, nm):
        mod = None
        for thing in self.path:
            if isinstance(thing, basestring):
                owner = self.shadowpath.get(thing, -1)
                if owner == -1:
                    owner = self.shadowpath[thing] = self.__makeOwner(thing)
                if owner:
                    mod = owner.getmod(nm)
            else:
                mod = thing.getmod(nm)
            if mod:
                break
        return mod

    def __makeOwner(self, path):
        if path in self.building:
            return None
        self.building.add(path)
        owner = None
        for klass in self.ownertypes:
            try:
                # this may cause an import, which may cause recursion
                # hence the protection
                owner = klass(path)
            except PyInstaller.depend.owner.OwnerError:
                pass
            except Exception, e:
                #print "FIXME: Wrong exception", e
                pass
            else:
                break
        self.building.remove(path)
        return owner
