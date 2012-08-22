#
# Copyright (C) 2005-2011, Giovanni Bajo
#
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#


### **NOTE** This module is used during bootstrap.
### Import *ONLY* builtin modules.
### List of built-in modules: sys.builtin_module_names
import sys
import imp
import marshal
import zipimport


def debug(msg):
    if 0:
        sys.stderr.write(msg + "\n")
        sys.stderr.flush()


#=======================Owners==========================#
# An Owner does imports from a particular piece of turf
# That is, there's an Owner for each thing on sys.path
# There are owners for directories and .pyz files.
# There could be owners for zip files, or even URLs.
# A shadowpath (a dictionary mapping the names in
# sys.path to their owners) is used so that sys.path
# (or a package's __path__) is still a bunch of strings,


class OwnerError(IOError):
    def __str__(self):
        return "<OwnerError %s>" % self.message


class Owner(object):
    """
    Base class for loading Python bytecode from different places.
    """
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return self.path

    def getmod(self, nm):
        return None


class DirOwner(Owner):
    """
    Load bytecode of Python modules from file system.
    """
    def __init__(self, path):
        if path == '':
            path = _os_getcwd()
        if not pathisdir(path):
            raise OwnerError("%s is not a directory" % path)
        Owner.__init__(self, path)

    def getmod(self, nm, getsuffixes=imp.get_suffixes,
               loadco=marshal.loads, newmod=imp.new_module):
        pth = _os_path_join(self.path, nm)
        possibles = [(pth, 0, None)]
        if pathisdir(pth) and caseOk(pth):
            possibles.insert(0, (_os_path_join(pth, '__init__'), 1, pth))
        py = pyc = None
        for pth, ispkg, pkgpth in possibles:
            for ext, mode, typ in getsuffixes():
                attempt = pth + ext
                try:
                    st = _os_stat(attempt)
                except OSError, e:
                    assert e.errno == 2  # [Errno 2] No such file or directory
                else:
                    # Check case
                    if not caseOk(attempt):
                        continue
                    if typ == imp.C_EXTENSION:
                        fp = open(attempt, 'rb')
                        mod = imp.load_module(nm, fp, attempt, (ext, mode, typ))
                        if hasattr(mod, "__setattr__"):
                            mod.__file__ = attempt
                        else:
                            # Some modules (eg: Python for .NET) have no __setattr__
                            # and dict entry have to be set
                            mod.__dict__["__file__"] = attempt
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
                    bytecode = compile(open(py[0], 'rU').read() + '\n', py[0], 'exec')
                    break
                except SyntaxError, e:
                    print "Invalid syntax in %s" % py[0]
                    print e.args
                    raise
            elif pyc:
                stuff = open(pyc[0], 'rb').read()
                try:
                    bytecode = loadco(stuff[8:])
                    break
                except (ValueError, EOFError):
                    pyc = None
            else:
                return None
        mod = newmod(nm)
        mod.__file__ = bytecode.co_filename
        if ispkg:
            mod.__path__ = [pkgpth]
            subimporter = PathImportDirector(mod.__path__)
            mod.__importsub__ = subimporter.getmod
        mod.__co__ = bytecode
        return mod


class ZipOwner(Owner):
    """
    Load bytecode of Python modules from .egg files.
    """
    def __init__(self, path):
        try:
            self.__zip = zipimport.zipimporter(path)
        except zipimport.ZipImportError, e:
            raise OwnerError('%s: %s' % (str(e), path))
        Owner.__init__(self, path)

    def getmod(self, nm, newmod=imp.new_module):
        # We cannot simply use zipimport.load_module here
        # because it both loads (= create module object)
        # and imports (= execute bytecode). Instead, our
        # getmod() functions are supposed to only load the modules.
        # Note that imp.load_module() does the right thing, instead.
        debug('zipimport try: %s within %s' % (nm, self.__zip))
        try:
            bytecode = self.__zip.get_code(nm)
            mod = newmod(nm)
            mod.__file__ = bytecode.co_filename
            if self.__zip.is_package(nm):
                mod.__path__ = [_os_path_join(self.path, nm)]
                subimporter = PathImportDirector(mod.__path__)
                mod.__importsub__ = subimporter.getmod
            if self.path.endswith(".egg"):
                # Fixup some additional special attribute so that
                # pkg_resources works correctly.
                # TODO: couldn't we fix these attributes always,
                # for all zip files?
                mod.__file__ = _os_path_join(
                    _os_path_join(self.path, nm), "__init__.py")
                mod.__loader__ = self.__zip
            mod.__co__ = bytecode
            return mod
        except zipimport.ZipImportError:
            debug('zipimport not found %s' % nm)
            return None


# Define order where to look for Python modules first.
# 1. PYZOwner: look in executable created by PyInstaller.
#    (_pyi_bootstrap.py will insert it (archive.PYZOwner) in front later.)
# 2. ZipOwner: zip files (.egg files)
# 3. DirOwner: file system
# 4. Owner:    module not found
_globalownertypes = [
    ZipOwner,
    DirOwner,
    Owner,
]


#===================Import Directors====================================#
# ImportDirectors live on the metapath
# There's one for builtins, one for frozen modules, and one for sys.path
# Mac would have them for PY_RESOURCE modules etc.
# A generalization of Owner - their concept of "turf" is broader


class ImportDirector(Owner):
    pass


class BuiltinImportDirector(ImportDirector):
    def __init__(self):
        self.path = 'Builtins'

    def getmod(self, nm, isbuiltin=imp.is_builtin):
        # Return initialized built-in module object or None
        # if there is no built-in module with that name.
        return imp.init_builtin(nm)


class PathImportDirector(ImportDirector):
    def __init__(self, pathlist=None, importers=None, ownertypes=None):
        self.path = pathlist
        if ownertypes == None:
            self.ownertypes = _globalownertypes
        else:
            self.ownertypes = ownertypes
        if importers:
            self.shadowpath = importers
        else:
            self.shadowpath = {}
        self.building = {}

    def __str__(self):
        return str(self.path or sys.path)

    def getmod(self, nm):
        mod = None
        for thing in (self.path or sys.path):
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
        self.building[path] = 1
        owner = None
        for klass in self.ownertypes:
            try:
                # this may cause an import, which may cause recursion
                # hence the protection
                owner = klass(path)
            except OwnerError:
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


class ImportManagerException(Exception):
    def __init__(self, args):
        self.args = args

    def __repr__(self):
        return "<%s: %s>" % (self.__name__, self.args)


class ImportManager(object):
    # really the equivalent of builtin import
    def __init__(self):
        self.metapath = [
            BuiltinImportDirector(),
            PathImportDirector()
        ]
        self.threaded = 0
        self.rlock = None
        self.locker = None
        self.setThreaded()

    def setThreaded(self):
        thread = sys.modules.get('thread', None)
        if thread and not self.threaded:
            #debug("iu setting threaded")
            self.threaded = 1
            self.rlock = thread.allocate_lock()
            self._get_ident = thread.get_ident

    def install(self):
        import __builtin__
        __builtin__.__import__ = self.importHook
        __builtin__.reload = self.reloadHook

    def importHook(self, name, globals=None, locals=None, fromlist=None, level=-1):
        __globals_name = None
        if globals:
            __globals_name = globals.get('__name__')
        # first see if we could be importing a relative name
        debug("importHook(%s, %s, locals, %s, %s)" % (name, __globals_name, fromlist, level))
        _sys_modules_get = sys.modules.get
        _self_doimport = self.doimport
        threaded = self.threaded

        # break the name being imported up so we get:
        # a.b.c -> [a, b, c]
        nmparts = namesplit(name)

        if not globals:
            contexts = [None]
            if level > 0:
                raise RuntimeError("Relative import requires 'globals'")
        elif level == 0:
            # absolute import, do not try relative
            contexts = [None]
        else:  # level != 0
            importernm = globals.get('__name__', '')
            ispkg = hasattr(_sys_modules_get(importernm), '__path__')
            debug('importernm %s' % importernm)
            if level < 0:
                # behaviour up to Python 2.4 (and default in Python 2.5)
                # add the package to searched contexts
                contexts = [None]
            else:
                # relative import, do not try absolute
                if not importernm:
                    raise RuntimeError("Relative import requires package")
                # level=1 => current package
                # level=2 => previous package => drop 1 level
                if level > 1:
                    importernm = importernm.split('.')[:-level + 1]
                    importernm = '.'.join(importernm)
                contexts = [None]
            if importernm:
                if ispkg:
                    # If you use the "from __init__ import" syntax, the package
                    # name will have a __init__ in it. We want to strip it.
                    if importernm[-len(".__init__"):] == ".__init__":
                        importernm = importernm[:-len(".__init__")]
                    contexts.insert(0, importernm)
                else:
                    pkgnm = packagename(importernm)
                    if pkgnm:
                        contexts.insert(0, pkgnm)

        # so contexts is [pkgnm, None], [pkgnm] or just [None]
        for context in contexts:
            ctx = context
            i = 0
            for i, nm in enumerate(nmparts):
                debug(" importHook trying %s in %s" % (nm, ctx))
                if ctx:
                    fqname = ctx + '.' + nm
                else:
                    fqname = nm
                if threaded:
                    self._acquire()
                try:
                    mod = _sys_modules_get(fqname, UNTRIED)
                    if mod is UNTRIED:
                        debug('trying %s %s %s' % (nm, ctx, fqname))
                        mod = _self_doimport(nm, ctx, fqname)
                finally:
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

        if i < len(nmparts):
            if ctx and hasattr(sys.modules[ctx], nmparts[i]):
                debug("importHook done with %s %s %s (case 1)" % (name, __globals_name, fromlist))
                return sys.modules[nmparts[0]]
            # Some executables may fail if 'fqname' is not in sys.modules.
            try:
                del sys.modules[fqname]
            except KeyError:
                pass
            raise ImportError("No module named %s" % fqname)
        if not fromlist:
            debug("importHook done with %s %s %s (case 2)" % (name, __globals_name, fromlist))
            if context:
                return sys.modules[context + '.' + nmparts[0]]
            return sys.modules[nmparts[0]]
        bottommod = sys.modules[ctx]
        if hasattr(bottommod, '__path__'):
            fromlist = list(fromlist)
            i = 0
            while i < len(fromlist):
                nm = fromlist[i]
                if nm == '*':
                    fromlist[i:i + 1] = list(getattr(bottommod, '__all__', []))
                    if i >= len(fromlist):
                        break
                    nm = fromlist[i]
                i = i + 1
                if not hasattr(bottommod, nm):
                    if threaded:
                        self._acquire()
                    try:
                        mod = self.doimport(nm, ctx, ctx + '.' + nm)
                    finally:
                        if threaded:
                            self._release()
        debug("importHook done with %s %s %s (case 3)" % (name, __globals_name, fromlist))
        return bottommod

    def doimport(self, nm, parentnm, fqname, reload=0):
        # Not that nm is NEVER a dotted name at this point
        debug("doimport(%s, %s, %s)" % (nm, parentnm, fqname))
        if parentnm:
            parent = sys.modules[parentnm]
            if hasattr(parent, '__path__'):
                importfunc = getattr(parent, '__importsub__', None)
                if not importfunc:
                    subimporter = PathImportDirector(parent.__path__)
                    importfunc = parent.__importsub__ = subimporter.getmod
                debug("using parent's importfunc: %s" % importfunc)
                mod = importfunc(nm)
                if mod and not reload:
                    setattr(parent, nm, mod)
            else:
                debug("..parent not a package")
                return None
        else:
            parent = None
            # now we're dealing with an absolute import
            for director in self.metapath:
                mod = director.getmod(nm)
                if mod:
                    break
        if mod:
            if hasattr(mod, "__setattr__"):
                mod.__name__ = fqname
            else:
                # Some modules (eg: Python for .NET) have no __setattr__
                # and dict entry have to be set
                mod.__dict__["__name__"] = fqname
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
                    # FIXME: how can we recover from a broken reload()?
                    # Should we save the mod dict and restore it in case
                    # of failure?
                    if not reload:
                        # Some modules (eg: dbhash.py) cleanup
                        # sys.modules themselves. We should then
                        # be lenient and avoid errors.
                        sys.modules.pop(fqname, None)
                        if hasattr(parent, nm):
                            delattr(parent, nm)
                    raise
            if fqname == 'thread' and not self.threaded:
                #debug("thread detected!")
                self.setThreaded()
        else:
            sys.modules[fqname] = None
        debug("..found %s when looking for %s" % (mod, fqname))
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
                #debug("_acquire incrementing lockcount to %s" % self.lockcount)
                return
        self.rlock.acquire()
        self.locker = self._get_ident()
        self.lockcount = 0
        #debug("_acquire first time!")

    def _release(self):
        if self.lockcount:
            self.lockcount = self.lockcount - 1
            #debug("_release decrementing lockcount to %s" % self.lockcount)
        else:
            self.locker = None
            self.rlock.release()
            #debug("_release releasing lock!")

#========= some helper functions =============================#


def packagename(s):
    """
    For package name like 'module.submodule.subsubmodule' returns
    'module.submodule'. If name does not contain any dots '.',
    empty string '' is returned.
    """
    i = s.rfind('.')
    if i >= 0:
        return s[:i]
    else:
        return ''


def namesplit(s):
    """
    Split package name at the position of dot '.'.

    Examples:
        'module.submodule' =>  ['module', 'submodule']
        'module'           =>  ['module']
        ''                 =>  []
    """
    rslt = []
    # Ensure that for empty string '' an empty list is returned.
    if s:
        rslt = s.split('.')
    return rslt


def getpathext(fnm):
    i = fnm.rfind('.')
    if i >= 0:
        return fnm[i:]
    else:
        return ''


def pathisdir(pathname):
    "Local replacement for os.path.isdir()."
    try:
        s = _os_stat(pathname)
    except OSError:
        return None
    return (s[0] & 0170000) == 0040000


_os_stat = _os_path_join = _os_getcwd = _os_path_dirname = None
_os_environ = _os_listdir = _os_path_basename = None
_os_sep = None


def _os_bootstrap():
    """
    Set up 'os' module replacement functions for use during import bootstrap.
    """

    global _os_stat, _os_getcwd, _os_environ, _os_listdir
    global _os_path_join, _os_path_dirname, _os_path_basename
    global _os_sep

    names = sys.builtin_module_names

    join = dirname = environ = listdir = basename = None
    mindirlen = 0
    # Only 'posix' and 'nt' os specific modules are supported.
    # 'dos', 'os2' and 'mac' (MacOS 9) are not supported.
    if 'posix' in names:
        from posix import stat, getcwd, environ, listdir
        sep = _os_sep = '/'
        mindirlen = 1
    elif 'nt' in names:
        from nt import stat, getcwd, environ, listdir
        sep = _os_sep = '\\'
        mindirlen = 3
    else:
        raise ImportError('no os specific module found')

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
            for i in range(len(a) - 1, -1, -1):
                c = a[i]
                if c == '/' or c == sep:
                    if i < mindirlen:
                        return a[:i + 1]
                    return a[:i]
            return ''

    if basename is None:
        def basename(p):
            i = p.rfind(sep)
            if i == -1:
                return p
            else:
                return p[i + len(sep):]

    def _listdir(dir, cache=None):
        # The cache is not used. It was found to cause problems
        # with programs that dynamically add python modules to be
        # reimported by that same program (i.e., plugins), because
        # the cache is only built once at the beginning, and never
        # updated. So, we must really list the directory again.
        return listdir(dir)

    _os_stat = stat
    _os_getcwd = getcwd
    _os_path_join = join
    _os_path_dirname = dirname
    _os_environ = environ
    _os_listdir = _listdir
    _os_path_basename = basename


_os_bootstrap()


if 'PYTHONCASEOK' not in _os_environ:
    def caseOk(filename):
        files = _os_listdir(_os_path_dirname(filename))
        return _os_path_basename(filename) in files
else:
    def caseOk(filename):
        return True
