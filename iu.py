# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# In addition to the permissions in the GNU General Public License, the
# authors give you unlimited permission to link or embed the compiled
# version of this file into combinations with other programs, and to
# distribute those combinations without any restriction coming from the
# use of this file. (The General Public License restrictions do apply in
# other respects; for example, they cover modification of the file, and
# distribution when not linked into a combine executable.)
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

# **NOTE** This module is used during bootstrap. Import *ONLY* builtin modules.
import sys
import imp
import marshal

try:
    py_version = sys.version_info
except AttributeError:
    py_version = (1,5)

#=======================Owners==========================#
# An Owner does imports from a particular piece of turf
# That is, there's an Owner for each thing on sys.path
# There are owners for directories and .pyz files.
# There could be owners for zip files, or even URLs.
# A shadowpath (a dictionary mapping the names in
# sys.path to their owners) is used so that sys.path
# (or a package's __path__) is still a bunch of strings,

STRINGTYPE = type('')

class Owner:
    def __init__(self, path):
        self.path = path
    def __str__(self):
        return self.path
    def getmod(self, nm):
        return None
class DirOwner(Owner):
    def __init__(self, path):
        if path == '':
            path = _os_getcwd()
        if not pathisdir(path):
            raise ValueError, "%s is not a directory" % path
        Owner.__init__(self, path)
    def getmod(self, nm, getsuffixes=imp.get_suffixes, loadco=marshal.loads, newmod=imp.new_module):
        pth =  _os_path_join(self.path, nm)
        possibles = [(pth, 0, None)]
        if pathisdir(pth):
            possibles.insert(0, (_os_path_join(pth, '__init__'), 1, pth))
        py = pyc = None
        for pth, ispkg, pkgpth in possibles:
            for ext, mode, typ in getsuffixes():
                attempt = pth+ext
                try:
                    st = _os_stat(attempt)
                except:
                    pass
                else:
                    if typ == imp.C_EXTENSION:
                        fp = open(attempt, 'rb')
                        mod = imp.load_module(nm, fp, attempt, (ext, mode, typ))
                        mod.__file__ = attempt
                        return mod
                    elif typ == imp.PY_SOURCE:
                        py = (attempt, st)
                    else:
                        pyc = (attempt, st)
            if py or pyc:
                break
        if py is None and pyc is None:
            return None
        while 1:
            if pyc is None or py and pyc[1][8] < py[1][8]:
                try:
                    co = compile(open(py[0], 'r').read()+'\n', py[0], 'exec')
                    break
                except SyntaxError, e:
                    print "Invalid syntax in %s" % py[0]
                    print e.args
                    raise
            elif pyc:
                stuff = open(pyc[0], 'rb').read()
                try:
                    co = loadco(stuff[8:])
                    break
                except (ValueError, EOFError):
                    pyc = None
            else:
                return None
        mod = newmod(nm)
        mod.__file__ = co.co_filename
        if ispkg:
            mod.__path__ = [pkgpth]
            subimporter = PathImportDirector(mod.__path__)
            mod.__importsub__ = subimporter.getmod
        mod.__co__ = co
        return mod

_globalownertypes = [
    DirOwner,
    Owner,
]

#===================Import Directors====================================#
# ImportDirectors live on the metapath
# There's one for builtins, one for frozen modules, and one for sys.path
# Windows gets one for modules gotten from the Registry
# Mac would have them for PY_RESOURCE modules etc.
# A generalization of Owner - their concept of "turf" is broader

class ImportDirector(Owner):
    pass
class BuiltinImportDirector(ImportDirector):
    def __init__(self):
        self.path = 'Builtins'
    def getmod(self, nm, isbuiltin=imp.is_builtin):
        if isbuiltin(nm):
            mod = imp.load_module(nm, None, nm, ('','',imp.C_BUILTIN))
            return mod
        return None
class FrozenImportDirector(ImportDirector):
    def __init__(self):
        self.path = 'FrozenModules'
    def getmod(self, nm, isfrozen=imp.is_frozen):
        if isfrozen(nm):
            mod = imp.load_module(nm, None, nm, ('','',imp.PY_FROZEN))
            if hasattr(mod, '__path__'):
                mod.__importsub__ = lambda name, pname=nm, owner=self: owner.getmod(pname+'.'+name)
            return mod
        return None
class RegistryImportDirector(ImportDirector):
    # for Windows only
    def __init__(self):
        self.path = "WindowsRegistry"
        self.map = {}
        try:
            import win32api
##            import win32con
        except ImportError:
            pass
        else:
            HKEY_CURRENT_USER = -2147483647
            HKEY_LOCAL_MACHINE = -2147483646
            KEY_ALL_ACCESS = 983103
            KEY_READ = 131097
            subkey = r"Software\Python\PythonCore\%s\Modules" % sys.winver
            for root in (HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE):
                try:
                    #hkey = win32api.RegOpenKeyEx(root, subkey, 0, KEY_ALL_ACCESS)
                    hkey = win32api.RegOpenKeyEx(root, subkey, 0, KEY_READ)
                except:
                    pass
                else:
                    numsubkeys, numvalues, lastmodified = win32api.RegQueryInfoKey(hkey)
                    for i in range(numsubkeys):
                        subkeyname = win32api.RegEnumKey(hkey, i)
                        #hskey = win32api.RegOpenKeyEx(hkey, subkeyname, 0, KEY_ALL_ACCESS)
                        hskey = win32api.RegOpenKeyEx(hkey, subkeyname, 0, KEY_READ)
                        val = win32api.RegQueryValueEx(hskey, '')
                        desc = getDescr(val[0])
                        self.map[subkeyname] = (val[0], desc)
                        hskey.Close()
                    hkey.Close()
                    break
    def getmod(self, nm):
        stuff = self.map.get(nm)
        if stuff:
            fnm, desc = stuff
            fp = open(fnm, 'rb')
            mod = imp.load_module(nm, fp, fnm, desc)
            mod.__file__ = fnm
            return mod
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
    def getmod(self, nm):
        mod = None
        for thing in self.path:
            if type(thing) is STRINGTYPE:
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
            except:
                pass
            else:
                break
        del self.building[path]
        return owner

def getDescr(fnm):
    ext = getpathext(fnm)
    for (suffix, mode, typ) in imp.get_suffixes():
        if suffix == ext:
            return (suffix, mode, typ)

#=================ImportManager============================#
# The one-and-only ImportManager
# ie, the builtin import

UNTRIED = -1

class ImportManager:
    # really the equivalent of builtin import
    def __init__(self):
        self.metapath = [
            BuiltinImportDirector(),
            FrozenImportDirector(),
            RegistryImportDirector(),
            PathImportDirector()
        ]
        self.threaded = 0
        self.rlock = None
        self.locker = None
        self.setThreaded()
    def setThreaded(self):
        thread = sys.modules.get('thread', None)
        if thread and not self.threaded:
##            print "iu setting threaded"
            self.threaded = 1
            self.rlock = thread.allocate_lock()
            self._get_ident = thread.get_ident
    def install(self):
        import __builtin__
        __builtin__.__import__ = self.importHook
        __builtin__.reload = self.reloadHook
    def importHook(self, name, globals=None, locals=None, fromlist=None):
        # first see if we could be importing a relative name
        #print "importHook(%s, %s, locals, %s)" % (name, globals['__name__'], fromlist)
        _sys_modules_get = sys.modules.get
        contexts = [None]
        if globals:
            importernm = globals.get('__name__', '')
            if importernm:
                if hasattr(_sys_modules_get(importernm), '__path__'):
                    # If you use the "from __init__ import" syntax, the package
                    # name will have a __init__ in it. We want to strip it.
                    if importernm[-len(".__init__"):] == ".__init__":
                        importernm = importernm[:-len(".__init__")]
                    contexts.insert(0,importernm)
                else:
                    pkgnm = packagename(importernm)
                    if pkgnm:
                        contexts.insert(0,pkgnm)
        # so contexts is [pkgnm, None] or just [None]
        # now break the name being imported up so we get:
        # a.b.c -> [a, b, c]
        nmparts = namesplit(name)
        _self_doimport = self.doimport
        threaded = self.threaded
        for context in contexts:
            ctx = context
            for i in range(len(nmparts)):
                nm = nmparts[i]
                #print " importHook trying %s in %s" % (nm, ctx)
                if ctx:
                    fqname = ctx + '.' + nm
                else:
                    fqname = nm
                if threaded:
                    self._acquire()
                mod = _sys_modules_get(fqname, UNTRIED)
                if mod is UNTRIED:
                    try:
                        mod = _self_doimport(nm, ctx, fqname)
                    except:
                        if threaded:
                            self._release()
                        raise
                if threaded:
                    self._release()
                if mod:
                    ctx = fqname
                else:
                    break
            else:
                # no break, point i beyond end
                i = i + 1
            if i:
                break

        if i<len(nmparts):
            if ctx and hasattr(sys.modules[ctx], nmparts[i]):
                #print "importHook done with %s %s %s (case 1)" % (name, globals['__name__'], fromlist)
                return sys.modules[nmparts[0]]
            del sys.modules[fqname]
            raise ImportError, "No module named %s" % fqname
        if fromlist is None:
            #print "importHook done with %s %s %s (case 2)" % (name, globals['__name__'], fromlist)
            if context:
                return sys.modules[context+'.'+nmparts[0]]
            return sys.modules[nmparts[0]]
        bottommod = sys.modules[ctx]
        if hasattr(bottommod, '__path__'):
            fromlist = list(fromlist)
            i = 0
            while i < len(fromlist):
                nm = fromlist[i]
                if nm == '*':
                    fromlist[i:i+1] = list(getattr(bottommod, '__all__', []))
                    if i >= len(fromlist):
                        break
                    nm = fromlist[i]
                i = i + 1
                if not hasattr(bottommod, nm):
                    if threaded:
                        self._acquire()
                    try:
                        mod = self.doimport(nm, ctx, ctx+'.'+nm)
                    except:
                        pass
                    if threaded:
                        self._release()
        #print "importHook done with %s %s %s (case 3)" % (name, globals['__name__'], fromlist)
        return bottommod
    def doimport(self, nm, parentnm, fqname, reload=0):
        # Not that nm is NEVER a dotted name at this point
        #print "doimport(%s, %s, %s)" % (nm, parentnm, fqname)
        if parentnm:
            parent = sys.modules[parentnm]
            if hasattr(parent, '__path__'):
                importfunc = getattr(parent, '__importsub__', None)
                if not importfunc:
                    subimporter = PathImportDirector(parent.__path__)
                    importfunc = parent.__importsub__ = subimporter.getmod
                mod = importfunc(nm)
                if mod and not reload:
                    setattr(parent, nm, mod)
            else:
                #print "..parent not a package"
                return None
        else:
            # now we're dealing with an absolute import
            for director in self.metapath:
                mod = director.getmod(nm)
                if mod:
                    break
        if mod:
            mod.__name__ = fqname
            if reload:
                sys.modules[fqname].__dict__.update(mod.__dict__)
            else:
                sys.modules[fqname] = mod
            if hasattr(mod, '__co__'):
                co = mod.__co__
                del mod.__co__
                try:
                    if reload:
                        exec co in sys.modules[fqname].__dict__
                    else:
                        exec co in mod.__dict__
                except:
                    # In Python 2.4 and above, sys.modules is left clean
                    # after a broken import. We need to do the same to
                    # achieve perfect compatibility (see ticket #32).
                    if py_version >= (2,4,0):
                        # FIXME: how can we recover from a broken reload()?
                        # Should we save the mod dict and restore it in case
                        # of failure?
                        if not reload:
                            del sys.modules[fqname]
                    raise
            if fqname == 'thread' and not self.threaded:
##                print "thread detected!"
                self.setThreaded()
        else:
            sys.modules[fqname] = None
        #print "..found %s" % mod
        return mod
    def reloadHook(self, mod):
        fqnm = mod.__name__
        nm = namesplit(fqnm)[-1]
        parentnm = packagename(fqnm)
        newmod = self.doimport(nm, parentnm, fqnm, reload=1)
        #mod.__dict__.update(newmod.__dict__)
        return newmod
    def _acquire(self):
        if self.rlock.locked():
            if self.locker == self._get_ident():
                self.lockcount = self.lockcount + 1
##                print "_acquire incrementing lockcount to", self.lockcount
                return
        self.rlock.acquire()
        self.locker = self._get_ident()
        self.lockcount = 0
##        print "_acquire first time!"
    def _release(self):
        if self.lockcount:
            self.lockcount = self.lockcount - 1
##            print "_release decrementing lockcount to", self.lockcount
        else:
            self.locker = None
            self.rlock.release()
##            print "_release releasing lock!"

#=========some helper functions=============================#

def packagename(s):
    for i in range(len(s)-1, -1, -1):
        if s[i] == '.':
            break
    else:
        return ''
    return s[:i]

def namesplit(s):
    rslt = []
    i = j = 0
    for j in range(len(s)):
        if s[j] == '.':
            rslt.append(s[i:j])
            i = j+1
    if i < len(s):
        rslt.append(s[i:])
    return rslt

def getpathext(fnm):
    for i in range(len(fnm)-1, -1, -1):
        if fnm[i] == '.':
            return fnm[i:]
    return ''

def pathisdir(pathname):
    "Local replacement for os.path.isdir()."
    try:
        s = _os_stat(pathname)
    except OSError:
        return None
    return (s[0] & 0170000) == 0040000

_os_stat = _os_path_join = _os_getcwd = _os_path_dirname = None
def _os_bootstrap():
    "Set up 'os' module replacement functions for use during import bootstrap."

    names = sys.builtin_module_names

    join = dirname = None
    mindirlen = 0
    if 'posix' in names:
        sep = '/'
        mindirlen = 1
        from posix import stat, getcwd
    elif 'nt' in names:
        sep = '\\'
        mindirlen = 3
        from nt import stat, getcwd
    elif 'dos' in names:
        sep = '\\'
        mindirlen = 3
        from dos import stat, getcwd
    elif 'os2' in names:
        sep = '\\'
        from os2 import stat, getcwd
    elif 'mac' in names:
        from mac import stat, getcwd
        def join(a, b):
            if a == '':
                return b
            path = s
            if ':' not in a:
                a = ':' + a
            if a[-1:] != ':':
                a = a + ':'
            return a + b
    else:
        raise ImportError, 'no os specific module found'

    if join is None:
        def join(a, b, sep=sep):
            if a == '':
                return b
            lastchar = a[-1:]
            if lastchar == '/' or lastchar == sep:
                return a + b
            return a + sep + b

    if dirname is None:
        def dirname(a, sep=sep, mindirlen=mindirlen):
            for i in range(len(a)-1, -1, -1):
                c = a[i]
                if c == '/' or c == sep:
                    if i < mindirlen:
                        return a[:i+1]
                    return a[:i]
            return ''

    global _os_stat
    _os_stat = stat

    global _os_path_join
    _os_path_join = join

    global _os_path_dirname
    _os_path_dirname = dirname

    global _os_getcwd
    _os_getcwd = getcwd

_string_replace = _string_join = _string_split = None
def _string_bootstrap():
    """
    Set up 'string' module replacement functions for use during import bootstrap.

    During bootstrap, we can use only builtin modules since import does not work
    yet. For Python 2.0+, we can use string methods so this is not a problem.
    For Python 1.5, we would need the string module, so we need replacements.
    """
    s = type('')

    global _string_replace, _string_join, _string_split

    if hasattr(s, "join"):
        _string_join = s.join
    else:
        def join(sep, words):
            res = ''
            for w in words:
                    res = res + (sep + w)
            return res[len(sep):]
        _string_join = join

    if hasattr(s, "split"):
        _string_split = s.split
    else:
        def split(s, sep, maxsplit=0):
            res = []
            nsep = len(sep)
            if nsep == 0:
                    return [s]
            ns = len(s)
            if maxsplit <= 0: maxsplit = ns
            i = j = 0
            count = 0
            while j+nsep <= ns:
                    if s[j:j+nsep] == sep:
                            count = count + 1
                            res.append(s[i:j])
                            i = j = j + nsep
                            if count >= maxsplit: break
                    else:
                            j = j + 1
            res.append(s[i:])
            return res
        _string_split = split

    if hasattr(s, "replace"):
        _string_replace = s.replace
    else:
        def replace(str, old, new):
            return _string_join(new, _string_split(str, old))
        _string_replace = replace



_os_bootstrap()
_string_bootstrap()
