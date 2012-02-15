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
#
import sys
import os
import imp
import marshal
import glob
import zipimport

from PyInstaller import depend, hooks
from PyInstaller.compat import caseOk, is_win, PYCO, set
from PyInstaller.loader import archive

import PyInstaller.log as logging

logger = logging.getLogger('PyInstaller.build.mf')

#=======================Owners==========================#
# An Owner does imports from a particular piece of turf
# That is, there's an Owner for each thing on sys.path
# There are owners for directories and .pyz files.
# There could be owners for zip files, or even URLs.
# Note that they replace the string in sys.path,
# but str(sys.path[n]) should yield the original string.


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
                        #print "DirOwner.getmod -> ExtensionModule(%s, %s)" % (nm, attempt)
                        return depend.modules.ExtensionModule(nm, os.path.join(self.path, attempt))
                    elif typ == imp.PY_SOURCE:
                        py = (attempt, modtime)
                    else:
                        pyc = (attempt, modtime)
            if py or pyc:
                break
        if py is None and pyc is None:
            #print "DirOwner.getmod -> (py == pyc == None)"
            return None
        while 1:
            # If we have no pyc or py is newer
            if pyc is None or py and pyc[1] < py[1]:
                try:
                    stuff = self._read(py[0]) + '\n'
                    co = compile(stuff.replace("\r\n", "\n"), py[0], 'exec')
                    pth = py[0] + PYCO
                    break
                except SyntaxError, e:
                    logger.exception(e)
                    raise SystemExit(10)
            elif pyc:
                stuff = self._read(pyc[0])
                # If this file was not generated for this version of
                # Python, we need to regenerate it.
                if stuff[:4] != imp.get_magic():
                    logger.warn("wrong version .pyc found (%s), will use .py",
                                pyc[0])
                    pyc = None
                    continue
                try:
                    co = loadco(stuff[8:])
                    pth = pyc[0]
                    break
                except (ValueError, EOFError):
                    logger.warn("bad .pyc found (%s), will use .py",
                                pyc[0])
                    pyc = None
            else:
                #print "DirOwner.getmod while 1 -> None"
                return None
        pth = os.path.join(self.path, pth)
        if not os.path.isabs(pth):
            pth = os.path.abspath(pth)
        if ispkg:
            mod = self._pkgclass()(nm, pth, co)
        else:
            mod = self._modclass()(nm, pth, co)
        #print "DirOwner.getmod -> %s" % mod
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


class PYZOwner(Owner):
    def __init__(self, path):
        self.pyz = archive.ZlibArchive(path)
        Owner.__init__(self, path)

    def getmod(self, nm):
        rslt = self.pyz.extract(nm)
        if not rslt:
            return None
        ispkg, co = rslt
        if ispkg:
            return depend.modules.PkgInPYZModule(nm, co, self)
        return depend.modules.PyModule(nm, self.path, co)


ZipOwner = None
if zipimport:
    # We cannot use zipimporter here because it has a stupid bug:
    #
    # >>> z.find_module("setuptools.setuptools.setuptools.setuptools.setuptools") is not None
    # True
    #
    # So mf will go into infinite recursion.
    # Instead, we'll reuse the BaseDirOwner logic, simply changing
    # the template methods.
    class ZipOwner(BaseDirOwner):
        """
        Load bytecode of Python modules from .egg files.
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

_globalownertypes = filter(None, [
    DirOwner,
    ZipOwner,
    PYZOwner,
    Owner,
])

#===================Import Directors====================================#
# ImportDirectors live on the metapath.
# There's one for builtins and one for sys.path.
# Windows gets one for modules gotten from the Registry
# There should be one for Frozen modules
# Mac would have them for PY_RESOURCE modules etc.
# A generalization of Owner - their concept of "turf" is broader


class ImportDirector(Owner):
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
            pass
        else:
            subkey = r"Software\Python\PythonCore\%s\Modules" % sys.winver
            for root in (win32con.HKEY_CURRENT_USER, win32con.HKEY_LOCAL_MACHINE):
                try:
                    #hkey = win32api.RegOpenKeyEx(root, subkey, 0, win32con.KEY_ALL_ACCESS)
                    hkey = win32api.RegOpenKeyEx(root, subkey, 0, win32con.KEY_READ)
                except Exception, e:
                    #print "RegistryImportDirector", e
                    pass
                else:
                    numsubkeys, numvalues, lastmodified = win32api.RegQueryInfoKey(hkey)
                    for i in range(numsubkeys):
                        subkeyname = win32api.RegEnumKey(hkey, i)
                        #hskey = win32api.RegOpenKeyEx(hkey, subkeyname, 0, win32con.KEY_ALL_ACCESS)
                        hskey = win32api.RegOpenKeyEx(hkey, subkeyname, 0, win32con.KEY_READ)
                        val = win32api.RegQueryValueEx(hskey, '')
                        desc = getDescr(val[0])
                        #print " RegistryImportDirector got %s %s" % (val[0], desc)  #XXX
                        self.map[subkeyname] = (val[0], desc)
                        hskey.Close()
                    hkey.Close()
                    break

    def getmod(self, nm):
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
    def __init__(self, pathlist=None, importers=None, ownertypes=None):
        if pathlist is None:
            self.path = sys.path
        else:
            self.path = pathlist
        if ownertypes == None:
            self.ownertypes = _globalownertypes
        else:
            self.ownertypes = ownertypes
        if importers:
            self.shadowpath = importers
        else:
            self.shadowpath = {}
        self.inMakeOwner = 0
        self.building = {}

    def __str__(self):
        return str(self.path)

    def getmod(self, nm):
        mod = None
        for thing in self.path:
            if isinstance(thing, basestring):
                owner = self.shadowpath.get(thing, -1)
                if owner == -1:
                    owner = self.shadowpath[thing] = self.makeOwner(thing)
                if owner:
                    mod = owner.getmod(nm)
            else:
                mod = thing.getmod(nm)
            if mod:
                break
        return mod

    def makeOwner(self, path):
        if self.building.get(path):
            return None
        self.building[path] = 1
        owner = None
        for klass in self.ownertypes:
            try:
                # this may cause an import, which may cause recursion
                # hence the protection
                owner = klass(path)
            except OwnerError:
                pass
            except Exception, e:
                #print "FIXME: Wrong exception", e
                pass
            else:
                break
        del self.building[path]
        return owner


def getDescr(fnm):
    ext = os.path.splitext(fnm)[1]
    for (suffix, mode, typ) in imp.get_suffixes():
        if suffix == ext:
            return (suffix, mode, typ)

#=================Import Tracker============================#
# This one doesn't really import, just analyzes
# If it *were* importing, it would be the one-and-only ImportManager
# ie, the builtin import

UNTRIED = -1

imptyps = ['top-level', 'conditional', 'delayed', 'delayed, conditional']

if __debug__:
    import UserDict

    class LogDict(UserDict.UserDict):
        count = 0

        def __init__(self, *args):
            UserDict.UserDict.__init__(self, *args)
            LogDict.count += 1
            logfile = "logdict%s-%d.log" % (".".join(map(str, sys.version_info)),
                                            LogDict.count)
            if os.path.isdir("build"):
                logfile = os.path.join("build", logfile)
            self.logfile = open(logfile, "w")

        def __setitem__(self, key, value):
            self.logfile.write("%s: %s -> %s\n" % (key, self.data.get(key), value))
            UserDict.UserDict.__setitem__(self, key, value)

        def __delitem__(self, key):
            self.logfile.write("  DEL %s\n" % key)
            UserDict.UserDict.__delitem__(self, key)
else:
    LogDict = dict


class ImportTracker:
    # really the equivalent of builtin import
    def __init__(self, xpath=None, hookspath=None, excludes=None):
        self.path = []
        self.warnings = {}
        if xpath:
            self.path = xpath
        self.path.extend(sys.path)
        self.modules = LogDict()

        # RegistryImportDirector is necessary only on Windows.
        if is_win:
            self.metapath = [
                BuiltinImportDirector(),
                RegistryImportDirector(),
                PathImportDirector(self.path)
            ]
        else:
            self.metapath = [
                BuiltinImportDirector(),
                PathImportDirector(self.path)
            ]

        if hookspath:
            hooks.__path__.extend(hookspath)
        if excludes is None:
            self.excludes = set()
        else:
            self.excludes = set(excludes)

    def analyze_r(self, nm, importernm=None):
        importer = importernm
        if importer is None:
            importer = '__main__'
        seen = {}
        nms = self.analyze_one(nm, importernm)
        nms = map(None, nms, [importer] * len(nms))
        i = 0
        while i < len(nms):
            nm, importer = nms[i]
            if seen.get(nm, 0):
                del nms[i]
                mod = self.modules[nm]
                if mod:
                    mod.xref(importer)
            else:
                i = i + 1
                seen[nm] = 1
                j = i
                mod = self.modules[nm]
                if mod:
                    mod.xref(importer)
                    for name, isdelayed, isconditional, level in mod.imports:
                        imptyp = isdelayed * 2 + isconditional
                        newnms = self.analyze_one(name, nm, imptyp, level)
                        newnms = map(None, newnms, [nm] * len(newnms))
                        nms[j:j] = newnms
                        j = j + len(newnms)
        return map(lambda a: a[0], nms)

    def analyze_one(self, nm, importernm=None, imptyp=0, level=-1):
        """
        break the name being imported up so we get:
        a.b.c -> [a, b, c] ; ..z -> ['', '', z]
        """
        #print '## analyze_one', nm, importernm, imptyp, level
        if not nm:
            nm = importernm
            importernm = None
            level = 0
        nmparts = nm.split('.')

        if level < 0:
            # behaviour up to Python 2.4 (and default in Python 2.5)
            # first see if we could be importing a relative name
            contexts = [None]
            if importernm:
                if self.ispackage(importernm):
                    contexts.insert(0, importernm)
                else:
                    pkgnm = ".".join(importernm.split(".")[:-1])
                    if pkgnm:
                        contexts.insert(0, pkgnm)
        elif level == 0:
            # absolute import, do not try relative
            importernm = None
            contexts = [None]
        elif level > 0:
            # relative import, do not try absolute
            if self.ispackage(importernm):
                level -= 1
            if level > 0:
                importernm = ".".join(importernm.split('.')[:-level])
            contexts = [importernm, None]
            importernm = None

        _all = None

        assert contexts

        # so contexts is [pkgnm, None] or just [None]
        if nmparts[-1] == '*':
            del nmparts[-1]
            _all = []
        nms = []
        for context in contexts:
            ctx = context
            for i, nm in enumerate(nmparts):
                if ctx:
                    fqname = ctx + '.' + nm
                else:
                    fqname = nm
                mod = self.modules.get(fqname, UNTRIED)
                if mod is UNTRIED:
                    logger.debug('Analyzing %s', fqname)
                    mod = self.doimport(nm, ctx, fqname)
                if mod:
                    nms.append(mod.__name__)
                    ctx = fqname
                else:
                    break
            else:
                # no break, point i beyond end
                i = i + 1
            if i:
                break
        # now nms is the list of modules that went into sys.modules
        # just as result of the structure of the name being imported
        # however, each mod has been scanned and that list is in mod.imports
        if i < len(nmparts):
            if ctx:
                if hasattr(self.modules[ctx], nmparts[i]):
                    return nms
                if not self.ispackage(ctx):
                    return nms
            self.warnings["W: no module named %s (%s import by %s)" % (fqname, imptyps[imptyp], importernm or "__main__")] = 1
            if fqname in self.modules:
                del self.modules[fqname]
            return nms
        if _all is None:
            return nms
        bottommod = self.modules[ctx]
        if bottommod.ispackage():
            for nm in bottommod._all:
                if not hasattr(bottommod, nm):
                    mod = self.doimport(nm, ctx, ctx + '.' + nm)
                    if mod:
                        nms.append(mod.__name__)
                    else:
                        bottommod.warnings.append("W: name %s not found" % nm)
        return nms

    def analyze_script(self, fnm):
        try:
            stuff = open(fnm, 'rU').read() + '\n'
            co = compile(stuff, fnm, 'exec')
        except SyntaxError, e:
            logger.exception(e)
            raise SystemExit(10)
        mod = depend.modules.PyScript(fnm, co)
        self.modules['__main__'] = mod
        return self.analyze_r('__main__')

    def ispackage(self, nm):
        return self.modules[nm].ispackage()

    def doimport(self, nm, ctx, fqname):
        """

        nm      name
                e.g.:
        ctx     context
                e.g.:
        fqname  fully qualified name
                e.g.:

        Return dict containing collected information about module (
        """

        #print "doimport", nm, ctx, fqname
        # NOTE that nm is NEVER a dotted name at this point
        assert ("." not in nm), nm
        if fqname in self.excludes:
            return None
        if ctx:
            parent = self.modules[ctx]
            if parent.ispackage():
                mod = parent.doimport(nm)
                if mod:
                    # insert the new module in the parent package
                    # FIXME why?
                    setattr(parent, nm, mod)
            else:
                # if parent is not a package, there is nothing more to do
                return None
        else:
            # now we're dealing with an absolute import
            # try to import nm using available directors
            for director in self.metapath:
                mod = director.getmod(nm)
                if mod:
                    break
        # here we have `mod` from:
        #   mod = parent.doimport(nm)
        # or
        #   mod = director.getmod(nm)
        if mod:
            mod.__name__ = fqname
            self.modules[fqname] = mod
            # now look for hooks
            # this (and scan_code) are instead of doing "exec co in mod.__dict__"
            try:
                hookmodnm = 'hook-' + fqname
                hooks = __import__('PyInstaller.hooks', globals(), locals(), [hookmodnm])
                hook = getattr(hooks, hookmodnm)
            except AttributeError:
                pass
            else:
                mod = self._handle_hook(mod, hook)
                if fqname != mod.__name__:
                    logger.warn("%s is changing it's name to %s",
                                fqname, mod.__name__)
                    self.modules[mod.__name__] = mod
        else:
            assert (mod == None), mod
            self.modules[fqname] = None
        # should be equivalent using only one
        # self.modules[fqname] = mod
        # here
        return mod

    def _handle_hook(self, mod, hook):
        if hasattr(hook, 'hook'):
            mod = hook.hook(mod)
        if hasattr(hook, 'hiddenimports'):
            for impnm in hook.hiddenimports:
                mod.imports.append((impnm, 0, 0, -1))
        if hasattr(hook, 'attrs'):
            for attr, val in hook.attrs:
                setattr(mod, attr, val)
        if hasattr(hook, 'datas'):
            # hook.datas is a list of globs of files or
            # directories to bundle as datafiles. For each
            # glob, a destination directory is specified.
            def _visit((base, dest_dir, datas), dirname, names):
                for fn in names:
                    fn = os.path.join(dirname, fn)
                    if os.path.isfile(fn):
                        datas.append((dest_dir + fn[len(base) + 1:], fn, 'DATA'))

            datas = mod.datas  # shortcut
            for g, dest_dir in hook.datas:
                if dest_dir:
                    dest_dir += os.sep
                for fn in glob.glob(g):
                    if os.path.isfile(fn):
                        datas.append((dest_dir + os.path.basename(fn), fn, 'DATA'))
                    else:
                        os.path.walk(fn, _visit,
                                     (os.path.dirname(fn), dest_dir, datas))
        return mod

    def getwarnings(self):
        warnings = self.warnings.keys()
        for nm, mod in self.modules.items():
            if mod:
                for w in mod.warnings:
                    warnings.append(w + ' - %s (%s)' % (mod.__name__, mod.__file__))
        return warnings

    def getxref(self):
        mods = self.modules.items()  # (nm, mod)
        mods.sort()
        rslt = []
        for nm, mod in mods:
            if mod:
                importers = mod._xref.keys()
                importers.sort()
                rslt.append((nm, importers))
        return rslt
