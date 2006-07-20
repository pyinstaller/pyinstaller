# Copyright (C) 2005, Giovanni Bajo
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
import sys, string, os, imp, marshal

#=======================Owners==========================#
# An Owner does imports from a particular piece of turf
# That is, there's an Owner for each thing on sys.path
# There are owners for directories and .pyz files.
# There could be owners for zip files, or even URLs.
# Note that they replace the string in sys.path,
# but str(sys.path[n]) should yield the original string.

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
            path = os.getcwd()
        if not os.path.isdir(path):
            raise ValueError, "%s is not a directory" % path
        Owner.__init__(self, path)
    def getmod(self, nm, getsuffixes=imp.get_suffixes, loadco=marshal.loads):
        pth =  os.path.join(self.path, nm)
        possibles = [(pth, 0, None)]
        if os.path.isdir(pth):
            possibles.insert(0, (os.path.join(pth, '__init__'), 1, pth))
        py = pyc = None
        for pth, ispkg, pkgpth in possibles:
            for ext, mode, typ in getsuffixes():
                attempt = pth+ext
                try:
                    st = os.stat(attempt)
                except:
                    pass
                else:
                    if typ == imp.C_EXTENSION:
                        return ExtensionModule(nm, attempt)
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
                    if __debug__:
                        pth = py[0] + 'c'
                    else:
                        pth = py[0] + 'o'
                    break
                except SyntaxError, e:
                    print "Syntax error in", py[0]
                    print e.args
                    raise
            elif pyc:
                stuff = open(pyc[0], 'rb').read()
                try:
                    co = loadco(stuff[8:])
                    pth = pyc[0]
                    break
                except (ValueError, EOFError):
                    print "W: bad .pyc found (%s)" % pyc[0]
                    pyc = None
            else:
                return None
        if not os.path.isabs(pth):
            pth = os.path.abspath(pth)
        if ispkg:
            mod = PkgModule(nm, pth, co)
        else:
            mod = PyModule(nm, pth, co)
        return mod

class PYZOwner(Owner):
    def __init__(self, path):
        import archive
        self.pyz = archive.ZlibArchive(path)
        Owner.__init__(self, path)
    def getmod(self, nm):
        rslt = self.pyz.extract(nm)
        if rslt:
            ispkg, co = rslt
        if ispkg:
            return PkgInPYZModule(nm, co, self)
        return PyModule(nm, self.path, co)

_globalownertypes = [
    DirOwner,
    PYZOwner,
    Owner,
]

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
                except:
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
                    co = compile(open(fnm, 'r').read()+'\n', fnm, 'exec')
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

class ImportTracker:
    # really the equivalent of builtin import
    def __init__(self, xpath=None, hookspath=None, excludes=None):
        self.path = []
        self.warnings = {}
        if xpath:
            self.path = xpath
        self.path.extend(sys.path)
        self.modules = {}
        self.metapath = [
            BuiltinImportDirector(),
            FrozenImportDirector(),
            RegistryImportDirector(),
            PathImportDirector(self.path)
        ]
        if hookspath:
            hooks.__path__.extend(hookspath)
        self.excludes = excludes
        if excludes is None:
            self.excludes = []
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
                    for name, isdelayed, isconditional in mod.imports:
                        imptyp = isdelayed * 2 + isconditional
                        newnms = self.analyze_one(name, nm, imptyp)
                        newnms = map(None, newnms, [nm]*len(newnms))
                        nms[j:j] = newnms
                        j = j + len(newnms)
        return map(lambda a: a[0], nms)
    def analyze_one(self, nm, importernm=None, imptyp=0):
        # first see if we could be importing a relative name
        contexts = [None]
        _all = None
        if importernm:
            if self.ispackage(importernm):
                contexts.insert(0,importernm)
            else:
                pkgnm = string.join(string.split(importernm, '.')[:-1], '.')
                if pkgnm:
                    contexts.insert(0,pkgnm)
        # so contexts is [pkgnm, None] or just [None]
        # now break the name being imported up so we get:
        # a.b.c -> [a, b, c]
        nmparts = string.split(nm, '.')
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
            co = compile(open(fnm, 'r').read()+'\n', fnm, 'exec')
        except SyntaxError, e:
            print "Invalid syntax in %s" % fnm
            print e.args
            raise
        mod = PyScript(fnm, co)
        self.modules['__main__'] = mod
        return self.analyze_r('__main__')


    def ispackage(self, nm):
        return self.modules[nm].ispackage()

    def doimport(self, nm, parentnm, fqname):
        # Not that nm is NEVER a dotted name at this point
        if fqname in self.excludes:
            return None
        if parentnm:
            parent = self.modules[parentnm]
            if parent.ispackage():
                mod = parent.doimport(nm)
                if mod:
                    setattr(parent, nm, mod)
            else:
                return None
        else:
            # now we're dealing with an absolute import
            for director in self.metapath:
                mod = director.getmod(nm)
                if mod:
                    break
        if mod:
            mod.__name__ = fqname
            self.modules[fqname] = mod
            # now look for hooks
            # this (and scan_code) are instead of doing "exec co in mod.__dict__"
            try:
                hookmodnm = 'hook-'+fqname
                hooks = __import__('hooks', globals(), locals(), [hookmodnm])
                hook = getattr(hooks, hookmodnm)
                #print `hook`
            except (ImportError, AttributeError):
                pass
            else:
                # rearranged so that hook() has a chance to mess with hiddenimports & attrs
                if hasattr(hook, 'hook'):
                    mod = hook.hook(mod)
                if hasattr(hook, 'hiddenimports'):
                    for impnm in hook.hiddenimports:
                        mod.imports.append((impnm, 0, 0))
                if hasattr(hook, 'attrs'):
                    for attr, val in hook.attrs:
                        setattr(mod, attr, val)

                if fqname != mod.__name__:
                    print "W: %s is changing it's name to %s" % (fqname, mod.__name__)
                    self.modules[mod.__name__] = mod
        else:
            self.modules[fqname] = None
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
        self._all = []
        self.imports = []
        self.warnings = []
        self._xref = {}
    def ispackage(self):
        return self._ispkg
    def doimport(self, nm):
        pass
    def xref(self, nm):
        self._xref[nm] = 1

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
            if __debug__:
                self.__file__ = self.__file__ + 'c'
            else:
                self.__file__ = self.__file__ + 'o'
        self.scancode()
    def scancode(self):
        self.imports, self.warnings, allnms = scan_code(self.co)
        if allnms:
            self._all = allnms

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
        self.subimporter = PathImportDirector(self.__path__)
    def doimport(self, nm):
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
LOAD_GLOBAL = dis.opname.index('LOAD_GLOBAL')
EXEC_STMT = dis.opname.index('EXEC_STMT')
try:
    SET_LINENO = dis.opname.index('SET_LINENO')
except ValueError:
    SET_LINENO = 999
BUILD_LIST = dis.opname.index('BUILD_LIST')
LOAD_CONST = dis.opname.index('LOAD_CONST')
JUMP_IF_FALSE = dis.opname.index('JUMP_IF_FALSE')
JUMP_IF_TRUE = dis.opname.index('JUMP_IF_TRUE')
JUMP_FORWARD = dis.opname.index('JUMP_FORWARD')
try:
    STORE_DEREF = dis.opname.index('STORE_DEREF')
except ValueError:
    STORE_DEREF = 999
COND_OPS = [JUMP_IF_TRUE, JUMP_IF_FALSE]
STORE_OPS = [STORE_NAME, STORE_FAST, STORE_GLOBAL, STORE_DEREF]
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
            out = i + oparg
        elif incondition and op == JUMP_FORWARD:
            out = max(out, i + oparg)
        if op == SET_LINENO:
            curline = oparg
        else:
            instrs.append((op, oparg, incondition, curline))
    return instrs

def scan_code(co, m=None, w=None, nested=0):
    instrs = pass1(co.co_code)
    if m is None:
        m = []
    if w is None:
        w = []
    all = None
    lastname = None
    for i in range(len(instrs)):
        op, oparg, conditional, curline = instrs[i]
        if op == IMPORT_NAME:
            name = lastname = co.co_names[oparg]
            m.append((name, nested, conditional))
        elif op == IMPORT_FROM:
            name = co.co_names[oparg]
            m.append((lastname+'.'+name, nested, conditional))
            assert lastname is not None
        elif op == IMPORT_STAR:
            m.append((lastname+'.*', nested, conditional))
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
    for c in co.co_consts:
        if isinstance(c, type(co)):
            scan_code(c, m, w, 1)
    return m, w, all
