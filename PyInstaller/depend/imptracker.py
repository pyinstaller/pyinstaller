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

import sys
import os
import glob

from PyInstaller import depend, hooks
from PyInstaller.compat import is_win, LogDict, set

import PyInstaller.log as logging
import PyInstaller.depend.owner
import PyInstaller.depend.impdirector

logger = logging.getLogger('PyInstaller.build.mf')


#=================Import Tracker============================#
# This one doesn't really import, just analyzes
# If it *were* importing, it would be the one-and-only ImportManager
# ie, the builtin import

UNTRIED = -1

imptyps = ['top-level', 'conditional', 'delayed', 'delayed, conditional']


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
                PyInstaller.depend.impdirector.BuiltinImportDirector(),
                PyInstaller.depend.impdirector.RegistryImportDirector(),
                PyInstaller.depend.impdirector.PathImportDirector(self.path)
            ]
        else:
            self.metapath = [
                PyInstaller.depend.impdirector.BuiltinImportDirector(),
                PyInstaller.depend.impdirector.PathImportDirector(self.path)
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
                    logger.warn("%s is changing its name to %s",
                                fqname, mod.__name__)
                    self.modules[mod.__name__] = mod
            # The following line has to be at the end of if statement because
            # 'mod' might be replaced by a new object within a hook.
            self.modules[fqname] = mod
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
