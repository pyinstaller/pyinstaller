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

import sys, string, os, imp, marshal, dircache, glob
try:
    # zipimport is supported starting with Python 2.3
    import zipimport
except ImportError:
    zipimport = None

try:
    # if ctypes is present, we can enable specific dependency discovery
    import ctypes
    from ctypes.util import find_library
except ImportError:
    ctypes = None

import suffixes

try:
    STRINGTYPE = basestring
except NameError:
    STRINGTYPE = type("")

if not os.environ.has_key('PYTHONCASEOK') and sys.version_info >= (2, 1):
    def caseOk(filename):
        files = dircache.listdir(os.path.dirname(filename))
        return os.path.basename(filename) in files
else:
    def caseOk(filename):
        return True

def pyco():
    """
    Returns correct extension ending: 'c' or 'o'
    """
    if __debug__:
        return 'c'
    else:
        return 'o'

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
    def __init__(self, path, target_platform=None):
        self.path = path
        self.target_platform = target_platform

    def __str__(self):
        return self.path

    def getmod(self, nm):
        return None

class BaseDirOwner(Owner):
    def _getsuffixes(self):
        return suffixes.get_suffixes(self.target_platform)

    def getmod(self, nm, getsuffixes=None, loadco=marshal.loads):
        if getsuffixes is None:
            getsuffixes = self._getsuffixes
        possibles = [(nm, 0, None)]
        if self._isdir(nm) and self._caseok(nm):
            possibles.insert(0, (os.path.join(nm, '__init__'), 1, nm))
        py = pyc = None
        for pth, ispkg, pkgpth in possibles:
            for ext, mode, typ in getsuffixes():
                attempt = pth+ext
                modtime = self._modtime(attempt)
                if modtime is not None:
                    # Check case
                    if not self._caseok(attempt):
                        continue
                    if typ == imp.C_EXTENSION:
                        #print "DirOwner.getmod -> ExtensionModule(%s, %s)" % (nm, attempt)
                        return ExtensionModule(nm, os.path.join(self.path,attempt))
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
                    stuff = self._read(py[0])+'\n'
                    co = compile(string.replace(stuff, "\r\n", "\n"), py[0], 'exec')
                    pth = py[0] + pyco()
                    break
                except SyntaxError, e:
                    print "Syntax error in", py[0]
                    print e.args
                    raise
            elif pyc:
                stuff = self._read(pyc[0])
                # If this file was not generated for this version of
                # Python, we need to regenerate it.
                if stuff[:4] != imp.get_magic():
                    print "W: wrong version .pyc found (%s), will use .py" % pyc[0]
                    pyc = None
                    continue
                try:
                    co = loadco(stuff[8:])
                    pth = pyc[0]
                    break
                except (ValueError, EOFError):
                    print "W: bad .pyc found (%s), will use .py" % pyc[0]
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
    def __init__(self, path, target_platform=None):
        if path == '':
            path = os.getcwd()
        if not os.path.isdir(path):
            raise OwnerError("%s is not a directory" % repr(path))
        Owner.__init__(self, path, target_platform)

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
        return PkgModule
    def _modclass(self):
        return PyModule
    def _caseok(self, fn):
        return caseOk(os.path.join(self.path, fn))

class PYZOwner(Owner):
    def __init__(self, path, target_platform=None):
        import archive
        self.pyz = archive.ZlibArchive(path)
        Owner.__init__(self, path, target_platform)
    def getmod(self, nm):
        rslt = self.pyz.extract(nm)
        if not rslt:
            return None
        ispkg, co = rslt
        if ispkg:
            return PkgInPYZModule(nm, co, self)
        return PyModule(nm, self.path, co)


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
        def __init__(self, path, target_platform=None):
            import zipfile
            try:
                self.zf = zipfile.ZipFile(path, "r")
            except IOError:
                raise OwnerError("%s is not a zipfile" % path)
            Owner.__init__(self, path, target_platform)
        def getmod(self, fn):
            fn = fn.replace(".", "/")
            return BaseDirOwner.getmod(self, fn)
        def _modtime(self, fn):
            fn = fn.replace("\\","/")
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
            fn = fn.replace("\\","/")
            return self.zf.read(fn)
        def _pkgclass(self):
            return lambda *args: PkgInZipModule(self, *args)
        def _modclass(self):
            return lambda *args: PyInZipModule(self, *args)

_globalownertypes = filter(None, [
    DirOwner,
    ZipOwner,
    PYZOwner,
    Owner,
])

#===================Import Directors====================================#
# ImportDirectors live on the metapath
# There's one for builtins, one for frozen modules, and one for sys.path
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
            return BuiltinModule(nm)
        return None

class FrozenImportDirector(ImportDirector):
    def __init__(self):
        self.path = 'FrozenModules'

    def getmod(self, nm, isfrozen=imp.is_frozen):
        if isfrozen(nm):
            return FrozenModule(nm)
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
                return ExtensionModule(nm, fnm)
            elif typ == imp.PY_SOURCE:
                try:
                    stuff = open(fnm, 'r').read()+'\n'
                    co = compile(string.replace(stuff, "\r\n", "\n"), fnm, 'exec')
                except SyntaxError, e:
                    print "Invalid syntax in %s" % py[0]
                    print e.args
                    raise
            else:
                stuff = open(fnm, 'rb').read()
                co = loadco(stuff[8:])
            return PyModule(nm, fnm, co)
        return None

class PathImportDirector(ImportDirector):
    def __init__(self, pathlist=None, importers=None, ownertypes=None,
                 target_platform=None):
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
        self.target_platform = target_platform

    def __str__(self):
        return str(self.path)

    def getmod(self, nm):
        mod = None
        for thing in self.path:
            if isinstance(thing, STRINGTYPE):
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
                owner = klass(path, self.target_platform)
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
import hooks

if __debug__:
    import sys
    import UserDict
    class LogDict(UserDict.UserDict):
        count = 0
        def __init__(self, *args):
            UserDict.UserDict.__init__(self, *args)
            LogDict.count += 1
            self.logfile = open("logdict%s-%d.log" % (".".join(map(str, sys.version_info)),
                                                      LogDict.count), "w")
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
    def __init__(self, xpath=None, hookspath=None, excludes=None,
                 target_platform=None):
        self.path = []
        self.warnings = {}
        if xpath:
            self.path = xpath
        self.path.extend(sys.path)
        self.modules = LogDict()
        self.metapath = [
            BuiltinImportDirector(),
            FrozenImportDirector(),
            RegistryImportDirector(),
            PathImportDirector(self.path, target_platform=target_platform)
        ]
        if hookspath:
            hooks.__path__.extend(hookspath)
        self.excludes = excludes
        if excludes is None:
            self.excludes = []
        self.target_platform = target_platform

    def analyze_r(self, nm, importernm=None):
        importer = importernm
        if importer is None:
            importer = '__main__'
        seen = {}
        nms = self.analyze_one(nm, importernm)
        nms = map(None, nms, [importer]*len(nms))
        i = 0
        while i < len(nms):
            nm, importer = nms[i]
            if seen.get(nm,0):
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
                        newnms = map(None, newnms, [nm]*len(newnms))
                        nms[j:j] = newnms
                        j = j + len(newnms)
        return map(lambda a: a[0], nms)

    def analyze_one(self, nm, importernm=None, imptyp=0, level=-1):
        #print '## analyze_one', nm, importernm, imptyp, level
        # break the name being imported up so we get:
        # a.b.c -> [a, b, c] ; ..z -> ['', '', z]
        if not nm:
            nm = importernm
            importernm = None
            level = 0
        nmparts = string.split(nm, '.')

        if level < 0:
            # behaviour up to Python 2.4 (and default in Python 2.5)
            # first see if we could be importing a relative name
            contexts = [None]
            if importernm:
                if self.ispackage(importernm):
                    contexts.insert(0, importernm)
                else:
                    pkgnm = string.join(string.split(importernm, '.')[:-1], '.')
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
                importernm = string.join(string.split(importernm, '.')[:-level], ".")
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
            for i in range(len(nmparts)):
                nm = nmparts[i]
                if ctx:
                    fqname = ctx + '.' + nm
                else:
                    fqname = nm
                mod = self.modules.get(fqname, UNTRIED)
                if mod is UNTRIED:
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
        if i<len(nmparts):
            if ctx:
                if hasattr(self.modules[ctx], nmparts[i]):
                    return nms
                if not self.ispackage(ctx):
                    return nms
            self.warnings["W: no module named %s (%s import by %s)" % (fqname, imptyps[imptyp], importernm or "__main__")] = 1
            if self.modules.has_key(fqname):
                del self.modules[fqname]
            return nms
        if _all is None:
            return nms
        bottommod = self.modules[ctx]
        if bottommod.ispackage():
            for nm in bottommod._all:
                if not hasattr(bottommod, nm):
                    mod = self.doimport(nm, ctx, ctx+'.'+nm)
                    if mod:
                        nms.append(mod.__name__)
                    else:
                        bottommod.warnings.append("W: name %s not found" % nm)
        return nms

    def analyze_script(self, fnm):
        try:
            stuff = open(fnm, 'r').read()+'\n'
            co = compile(string.replace(stuff, "\r\n", "\n"), fnm, 'exec')
        except SyntaxError, e:
            print "Invalid syntax in %s" % fnm
            print e.args
            raise
        mod = PyScript(fnm, co)
        self.modules['__main__'] = mod
        return self.analyze_r('__main__')


    def ispackage(self, nm):
        return self.modules[nm].ispackage()

    def doimport(self, nm, ctx, fqname):
        #print "doimport", nm, ctx, fqname
        # Not that nm is NEVER a dotted name at this point
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
                hookmodnm = 'hook-'+fqname
                hooks = __import__('hooks', globals(), locals(), [hookmodnm])
                hook = getattr(hooks, hookmodnm)
            except AttributeError:
                pass
            else:
                # rearranged so that hook() has a chance to mess with hiddenimports & attrs
                if hasattr(hook, 'hook'):
                    mod = hook.hook(mod)
                if hasattr(hook, 'hiddenimports'):
                    for impnm in hook.hiddenimports:
                        mod.imports.append((impnm, 0, 0, -1))
                if hasattr(hook, 'attrs'):
                    for attr, val in hook.attrs:
                        setattr(mod, attr, val)
                if hasattr(hook, 'datas'):
                    # hook.datas is a list of globs of files or directories to bundle
                    # as datafiles. For each glob, a destination directory is specified.
                    for g,dest_dir in hook.datas:
                        if dest_dir: dest_dir += "/"
                        for fn in glob.glob(g):
                            if os.path.isfile(fn):
                                mod.datas.append((dest_dir + os.path.basename(fn), fn, 'DATA'))
                            else:
                                def visit((base,dest_dir,datas), dirname, names):
                                    for fn in names:
                                        fn = os.path.join(dirname, fn)
                                        if os.path.isfile(fn):
                                            datas.append((dest_dir + fn[len(base)+1:], fn, 'DATA'))
                                os.path.walk(fn, visit, (os.path.dirname(fn),dest_dir,mod.datas))
                if fqname != mod.__name__:
                    print "W: %s is changing it's name to %s" % (fqname, mod.__name__)
                    self.modules[mod.__name__] = mod
        else:
            assert (mod == None), mod
            self.modules[fqname] = None
        # should be equivalent using only one
        # self.modules[fqname] = mod
        # here
        return mod

    def getwarnings(self):
        warnings = self.warnings.keys()
        for nm,mod in self.modules.items():
            if mod:
                for w in mod.warnings:
                    warnings.append(w+' - %s (%s)' % (mod.__name__, mod.__file__))
        return warnings

    def getxref(self):
        mods = self.modules.items() # (nm, mod)
        mods.sort()
        rslt = []
        for nm, mod in mods:
            if mod:
                importers = mod._xref.keys()
                importers.sort()
                rslt.append((nm, importers))
        return rslt

#====================Modules============================#
# All we're doing here is tracking, not importing
# If we were importing, these would be hooked to the real module objects

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
        return "<Module %s %s imports=%s binaries=%s datas=%s>" % \
            (self.__name__, self.__file__, self.imports, self.binaries, self.datas)

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
            self.__file__ = self.__file__ + pyco()
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
        self.__path__ = [ pth ]
        self._update_director(force=True)

    def _update_director(self, force=False):
        if force or self.subimporter.path != self.__path__:
            self.subimporter = PathImportDirector(self.__path__)

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
        self.__path__ = [ str(pyzowner) ]
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
        self.__path__ = [ str(zipowner) ]
        self.owner = zipowner

    def doimport(self, nm):
        mod = self.owner.getmod(self.__name__ + '.' + nm)
        return mod


#======================== Utility ================================#
# Scan the code object for imports, __all__ and wierd stuff

import dis
IMPORT_NAME = dis.opname.index('IMPORT_NAME')
IMPORT_FROM = dis.opname.index('IMPORT_FROM')
try:
    IMPORT_STAR = dis.opname.index('IMPORT_STAR')
except:
    IMPORT_STAR = 999
STORE_NAME = dis.opname.index('STORE_NAME')
STORE_FAST = dis.opname.index('STORE_FAST')
STORE_GLOBAL = dis.opname.index('STORE_GLOBAL')
try:
    STORE_MAP = dis.opname.index('STORE_MAP')
except:
    STORE_MAP = 999
LOAD_GLOBAL = dis.opname.index('LOAD_GLOBAL')
LOAD_ATTR = dis.opname.index('LOAD_ATTR')
LOAD_NAME = dis.opname.index('LOAD_NAME')
EXEC_STMT = dis.opname.index('EXEC_STMT')
try:
    SET_LINENO = dis.opname.index('SET_LINENO')
except ValueError:
    SET_LINENO = 999
BUILD_LIST = dis.opname.index('BUILD_LIST')
LOAD_CONST = dis.opname.index('LOAD_CONST')
if getattr(sys, 'version_info', (0,0,0)) > (2,5,0):
    LOAD_CONST_level = LOAD_CONST
else:
    LOAD_CONST_level = 999
if getattr(sys, 'version_info', (0,0,0)) >= (2,7,0):
    COND_OPS = [dis.opname.index('POP_JUMP_IF_TRUE'),
                dis.opname.index('POP_JUMP_IF_FALSE'),
                dis.opname.index('JUMP_IF_TRUE_OR_POP'),
                dis.opname.index('JUMP_IF_FALSE_OR_POP'),
               ]
else:
    COND_OPS = [dis.opname.index('JUMP_IF_FALSE'),
                dis.opname.index('JUMP_IF_TRUE'),
               ]
JUMP_FORWARD = dis.opname.index('JUMP_FORWARD')
try:
    STORE_DEREF = dis.opname.index('STORE_DEREF')
except ValueError:
    STORE_DEREF = 999
STORE_OPS = [STORE_NAME, STORE_FAST, STORE_GLOBAL, STORE_DEREF, STORE_MAP]
#IMPORT_STAR -> IMPORT_NAME mod ; IMPORT_STAR
#JUMP_IF_FALSE / JUMP_IF_TRUE / JUMP_FORWARD

def pass1(code):
    instrs = []
    i = 0
    n = len(code)
    curline = 0
    incondition = 0
    out = 0
    while i < n:
        if i >= out:
            incondition = 0
        c = code[i]
        i = i+1
        op = ord(c)
        if op >= dis.HAVE_ARGUMENT:
            oparg = ord(code[i]) + ord(code[i+1])*256
            i = i+2
        else:
            oparg = None
        if not incondition and op in COND_OPS:
            incondition = 1
            out = oparg
            if op in dis.hasjrel:
                out += i
        elif incondition and op == JUMP_FORWARD:
            out = max(out, i + oparg)
        if op == SET_LINENO:
            curline = oparg
        else:
            instrs.append((op, oparg, incondition, curline))
    return instrs

def scan_code(co, m=None, w=None, b=None, nested=0):
    instrs = pass1(co.co_code)
    if m is None:
        m = []
    if w is None:
        w = []
    if b is None:
        b = []
    all = None
    lastname = None
    level = -1 # import-level, same behaviour as up to Python 2.4
    for i in range(len(instrs)):
        op, oparg, conditional, curline = instrs[i]
        if op == IMPORT_NAME:
            if level <= 0:
                name = lastname = co.co_names[oparg]
            else:
                name = lastname = co.co_names[oparg]
            #print 'import_name', name, `lastname`, level
            m.append((name, nested, conditional, level))
        elif op == IMPORT_FROM:
            name = co.co_names[oparg]
            #print 'import_from', name, `lastname`, level,
            if level > 0 and (not lastname or lastname[-1:] == '.'):
                name = lastname + name
            else:
                name = lastname + '.' + name
            #print name
            m.append((name, nested, conditional, level))
            assert lastname is not None
        elif op == IMPORT_STAR:           
            assert lastname is not None
            m.append((lastname+'.*', nested, conditional, level))
        elif op == STORE_NAME:
            if co.co_names[oparg] == "__all__":
                j = i - 1
                pop, poparg, pcondtl, pline = instrs[j]
                if pop != BUILD_LIST:
                    w.append("W: __all__ is built strangely at line %s" % pline)
                else:
                    all = []
                    while j > 0:
                        j = j - 1
                        pop, poparg, pcondtl, pline = instrs[j]
                        if pop == LOAD_CONST:
                            all.append(co.co_consts[poparg])
                        else:
                            break
        elif op in STORE_OPS:
            pass
        elif op == LOAD_CONST_level:
            # starting with Python 2.5, _each_ import is preceeded with a
            # LOAD_CONST to indicate the relative level.
            if isinstance(co.co_consts[oparg], (int, long)):
                level = co.co_consts[oparg]
        elif op == LOAD_GLOBAL:
            name = co.co_names[oparg]
            cndtl = ['', 'conditional'][conditional]
            lvl = ['top-level', 'delayed'][nested]
            if name == "__import__":
                w.append("W: %s %s __import__ hack detected at line %s"  % (lvl, cndtl, curline))
            elif name == "eval":
                w.append("W: %s %s eval hack detected at line %s"  % (lvl, cndtl, curline))
        elif op == EXEC_STMT:
            cndtl = ['', 'conditional'][conditional]
            lvl = ['top-level', 'delayed'][nested]
            w.append("W: %s %s exec statement detected at line %s"  % (lvl, cndtl, curline))
        else:
            lastname = None

        if ctypes:
            # ctypes scanning requires a scope wider than one bytecode instruction,
            # so the code resides in a separate function for clarity.
            ctypesb, ctypesw = scan_code_for_ctypes(co, instrs, i)
            b.extend(ctypesb)
            w.extend(ctypesw)

    for c in co.co_consts:
        if isinstance(c, type(co)):
            # FIXME: "all" was not updated here nor returned. Was it the desired
            # behaviour?
            _, _, _, all_nested = scan_code(c, m, w, b, 1)
            if all_nested:
                all.extend(all_nested)
    return m, w, b, all

def scan_code_for_ctypes(co, instrs, i):
    """Detects ctypes dependencies, using reasonable heuristics that should
    cover most common ctypes usages; returns a tuple of two lists, one
    containing names of binaries detected as dependencies, the other containing
    warnings.
    """

    def _libFromConst(i):
        """Extracts library name from an expected LOAD_CONST instruction and
        appends it to local binaries list.
        """
        op, oparg, conditional, curline = instrs[i]
        if op == LOAD_CONST:
            soname = co.co_consts[oparg]
            b.append(soname)

    b = []

    op, oparg, conditional, curline = instrs[i]

    if op in (LOAD_GLOBAL, LOAD_NAME):
        name = co.co_names[oparg]

        if name in ("CDLL", "WinDLL"):
            # Guesses ctypes imports of this type: CDLL("library.so")

            # LOAD_GLOBAL 0 (CDLL) <--- we "are" here right now
            # LOAD_CONST 1 ('library.so')

            _libFromConst(i+1)

        elif name == "ctypes":
            # Guesses ctypes imports of this type: ctypes.DLL("library.so")

            # LOAD_GLOBAL 0 (ctypes) <--- we "are" here right now
            # LOAD_ATTR 1 (CDLL)
            # LOAD_CONST 1 ('library.so')

            op2, oparg2, conditional2, curline2 = instrs[i+1]
            if op2 == LOAD_ATTR:
                if co.co_names[oparg2] in ("CDLL", "WinDLL"):
                    # Fetch next, and finally get the library name
                    _libFromConst(i+2)

        elif name in ("cdll", "windll"):
            # Guesses ctypes imports of these types:

            #  * cdll.library (only valid on Windows)

            #     LOAD_GLOBAL 0 (cdll) <--- we "are" here right now
            #     LOAD_ATTR 1 (library)

            #  * cdll.LoadLibrary("library.so")

            #     LOAD_GLOBAL              0 (cdll) <--- we "are" here right now
            #     LOAD_ATTR                1 (LoadLibrary)
            #     LOAD_CONST               1 ('library.so')

            op2, oparg2, conditional2, curline2 = instrs[i+1]
            if op2 == LOAD_ATTR:
                if co.co_names[oparg2] != "LoadLibrary":
                    # First type
                    soname = co.co_names[oparg2] + ".dll"
                    b.append(soname)
                else:
                    # Second type, needs to fetch one more instruction
                    _libFromConst(i+2)

    # If any of the libraries has been requested with anything different from
    # the bare filename, drop that entry and warn the user - pyinstaller would
    # need to patch the compiled pyc file to make it work correctly!

    w = []
    for bin in list(b):
        if bin != os.path.basename(bin):
            b.remove(bin)
            w.append("W: ignoring %s - ctypes imports only supported using bare filenames" % (bin,))

    return b, w


def _resolveCtypesImports(cbinaries):
    """Completes ctypes BINARY entries for modules with their full path.
    """
    if sys.platform.startswith("linux"):
        envvar = "LD_LIBRARY_PATH"
    elif sys.platform.startswith("darwin"):
        envvar = "DYLD_LIBRARY_PATH"
    else:
        envvar = "PATH"

    def _savePaths():
        old = os.environ.get(envvar, None)
        os.environ[envvar] = os.pathsep.join(getattr(sys, "pathex", []))
        if old is not None:
            os.environ[envvar] = os.pathsep.join([os.environ[envvar], old])
        return old

    def _restorePaths(old):
        del os.environ[envvar]
        if old is not None:
            os.environ[envvar] = old

    ret = []

    # Try to locate the shared library on disk. This is done by
    # executing ctypes.utile.find_library prepending ImportTracker's
    # local paths to library search paths, then replaces original values.
    old = _savePaths()
    for cbin in cbinaries:
        ext = os.path.splitext(cbin)[1]
        # On Windows, only .dll files can be loaded.
        if os.name == "nt" and ext.lower() in [".so", ".dylib"]:
            continue
        cpath = find_library(os.path.splitext(cbin)[0])
        if sys.platform == "linux2":
            # CAVEAT: find_library() is not the correct function. Ctype's
            # documentation says that it is meant to resolve only the filename
            # (as a *compiler* does) not the full path. Anyway, it works well
            # enough on Windows and Mac. On Linux, we need to implement
            # more code to find out the full path.
            if cpath is None:
                cpath = cbin
            # "man ld.so" says that we should first search LD_LIBRARY_PATH
            # and then the ldcache
            for d in os.environ["LD_LIBRARY_PATH"].split(":"):
                if os.path.isfile(d + "/" + cpath):
                    cpath = d + "/" + cpath
                    break
            else:
                for L in os.popen("ldconfig -p").read().splitlines():
                    if cpath in L:
                        cpath = L.split("=>", 1)[1].strip()
                        assert os.path.isfile(cpath)
                        break
                else:
                    cpath = None
        if cpath is None:
            print "W: library %s required via ctypes not found" % (cbin,)
        else:
            ret.append((cbin, cpath, "BINARY"))
    _restorePaths(old)
    return ret


