#! /usr/bin/env python
# Build packages using spec files
# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 1999, 2002 McMillan Enterprises, Inc.
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
import sys, os, shutil, mf, archive, iu, carchive, pprint, time, py_compile, bindepend, tempfile

STRINGTYPE = type('')
TUPLETYPE = type((None,))

HOMEPATH = os.path.dirname(sys.argv[0])
SPECPATH = None
BUILDPATH = None
WARNFILE = None
rthooks = {}
iswin = sys.platform[:3] == 'win'
cygwin = sys.platform == 'cygwin'
try:
    config = eval(open(os.path.join(HOMEPATH, 'config.dat'), 'r').read())
except IOError:
    print "You must run Configure.py before building!"
    sys.exit(1)

if config['pythonVersion'] != sys.version:
    print "The current version of Python is not the same with which PyInstaller was configured."
    print "Please re-run Configure.py with this version."
    sys.exit(1)

if config['hasRsrcUpdate']:
    import icon, versionInfo

def setupUPXFlags():
    f = os.environ.get("UPX", "")
    is24 = hasattr(sys, "version_info") and sys.version_info[:2] >= (2,4)
    if iswin and is24:
        # Binaries built with Visual Studio 7.1 require --strip-loadconf
        # or they won't compress. Configure.py makes sure that UPX is new
        # enough to support --strip-loadconf.
        f = "--strip-loadconf " + f
    f = "--best " + f
    os.environ["UPX"] = f

if config['hasUPX']:
    setupUPXFlags()

def build(spec):
    global SPECPATH, BUILDPATH, WARNFILE, rthooks
    rthooks = eval(open(os.path.join(HOMEPATH, 'rthooks.dat'), 'r').read())
    SPECPATH, specnm = os.path.split(spec)
    specnm = os.path.splitext(specnm)[0]
    if SPECPATH == '':
        SPECPATH = os.getcwd()
    WARNFILE = os.path.join(SPECPATH, 'warn%s.txt' % specnm)
    BUILDPATH = os.path.join(SPECPATH, 'build%s' % specnm)
    if '-o' in sys.argv:
        bpath = sys.argv[sys.argv.index('-o')+1]
        if os.path.isabs(bpath):
            BUILDPATH = bpath
        else:
            BUILDPATH = os.path.join(SPECPATH, bpath)
    if not os.path.exists(BUILDPATH):
        os.mkdir(BUILDPATH)
    exec open(spec, 'r').read()+'\n'

def mtime(fnm):
    try:
        return os.stat(fnm)[8]
    except:
        return 0

class Target:
    invcnum = 0
    def __init__(self):
        self.invcnum = Target.invcnum
        Target.invcnum = Target.invcnum + 1
        self.out = os.path.join(BUILDPATH, 'out%d.toc' % self.invcnum)
        self.dependencies = TOC()
    def __postinit__(self):
        print "checking %s" % (self.__class__.__name__,)
        if self.check_guts(mtime(self.out)):
            self.assemble()

class Analysis(Target):
    def __init__(self, scripts=None, pathex=None, hookspath=None, excludes=None):
        Target.__init__(self)
        self.inputs = scripts
        for script in scripts:
            if not os.path.exists(script):
                raise ValueError, "script '%s' not found" % script
        self.pathex = []
        if pathex:
            for path in pathex:
                self.pathex.append(os.path.abspath(os.path.normpath(path)))
        self.hookspath = hookspath
        self.excludes = excludes
        self.scripts = TOC()
        self.pure = TOC()
        self.binaries = TOC()
        self.__postinit__()
    def check_guts(self, last_build):
        outnm = os.path.basename(self.out)
        if last_build == 0:
            print "building %s because %s non existent" % (self.__class__.__name__, outnm)
            return 1
        for fnm in self.inputs:
            if mtime(fnm) > last_build:
                print "building because %s changed" % fnm
                return 1
        try:
            inputs, pathex, hookspath, excludes, scripts, pure, binaries = eval(open(self.out, 'r').read())
        except:
            print "building because %s disappeared" % outnm
            return 1
        if inputs != self.inputs:
            print "building %s because inputs changed" % outnm
            return 1
        if pathex != self.pathex:
            print "building %s because pathex changed" % outnm
            return 1
        if hookspath != self.hookspath:
            print "building %s because hookspath changed" % outnm
            return 1
        if excludes != self.excludes:
            print "building %s because excludes changed" % outnm
            return 1
        for (nm, fnm, typ) in scripts:
            if mtime(fnm) > last_build:
                print "building because %s changed" % fnm
                return 1
        for (nm, fnm, typ) in pure:
            if mtime(fnm) > last_build:
                print "building because %s changed" % fnm
                return 1
            elif mtime(fnm[:-1]) > last_build:
                print "building because %s changed" % fnm[:-1]
                return 1
        for (nm, fnm, typ) in binaries:
            if mtime(fnm) > last_build:
                print "building because %s changed" % fnm
                return 1
        self.scripts = TOC(scripts)
        self.pure = TOC(pure)
        self.binaries = TOC(binaries)
        return 0
    def assemble(self):
        print "running Analysis", os.path.basename(self.out)
        paths = self.pathex
        for i in range(len(paths)):
            paths[i] = os.path.abspath(os.path.normpath(paths[i]))
        dirs = {}
        pynms = []
        for script in self.inputs:
            if not os.path.exists(script):
                print "Analysis: script %s not found!" % script
                sys.exit(1)
            d, base = os.path.split(script)
            if not d:
                d = os.getcwd()
            d = os.path.abspath(os.path.normpath(d))
            pynm, ext = os.path.splitext(base)
            dirs[d] = 1
            pynms.append(pynm)
        analyzer = mf.ImportTracker(dirs.keys()+paths, self.hookspath, self.excludes)
        #print analyzer.path
        scripts = []
        for i in range(len(self.inputs)):
            script = self.inputs[i]
            print "Analyzing:", script
            analyzer.analyze_script(script)
            scripts.append((pynms[i], script, 'PYSOURCE'))
        pure = []
        binaries = []
        rthooks = []
        for modnm, mod in analyzer.modules.items():
            if mod is not None:
                hooks = findRTHook(modnm)  #XXX
                if hooks:
                    rthooks.extend(hooks)
                if isinstance(mod, mf.BuiltinModule):
                    pass
                else:
                    fnm = mod.__file__
                    if isinstance(mod, mf.ExtensionModule):
                        binaries.append((mod.__name__, fnm, 'EXTENSION'))
                    elif modnm == '__main__':
                        pass
                    else:
                        pure.append((modnm, fnm, 'PYMODULE'))
        binaries.extend(bindepend.Dependencies(binaries))
        scripts[1:1] = rthooks
        self.scripts = TOC(scripts)
        self.pure = TOC(pure)
        self.binaries = TOC(binaries)
        try:
            oldstuff = eval(open(self.out, 'r').read())
        except:
            oldstuff = None
        if oldstuff != (self.inputs, self.pathex, self.hookspath, self.excludes, scripts, pure, binaries):
            outf = open(self.out, 'w')
            pprint.pprint(
                (self.inputs, self.pathex, self.hookspath, self.excludes, self.scripts, self.pure, self.binaries),
                outf)
            outf.close()
            wf = open(WARNFILE, 'w')
            for ln in analyzer.getwarnings():
                wf.write(ln+'\n')
            wf.close()
            print "Warnings written to %s" % WARNFILE
            return 1
        print self.out, "no change!"
        return 0

def findRTHook(modnm):
    hooklist = rthooks.get(modnm)
    if hooklist:
        rslt = []
        for script in hooklist:
            nm = os.path.basename(script)
            nm = os.path.splitext(nm)[0]
            if os.path.isabs(script):
                path = script
            else:
                path = os.path.join(HOMEPATH, script)
            rslt.append((nm, path, 'PYSOURCE'))
        return rslt
    return None

class PYZ(Target):
    typ = 'PYZ'
    def __init__(self, toc, name=None, level=9):
        Target.__init__(self)
        self.toc = toc
        self.name = name
        if name is None:
            self.name = self.out[:-3] + 'pyz'
        if config['useZLIB']:
            self.level = level
        else:
            self.level = 0
        self.dependencies = config['PYZ_dependencies']
        self.__postinit__()
    def check_guts(self, last_build):
        outnm = os.path.basename(self.out)
        if not os.path.exists(self.name):
            print "rebuilding %s because %s is missing" % (outnm, os.path.basename(self.name))
            return 1
        try:
            name, level, toc = eval(open(self.out, 'r').read())
        except:
            print "rebuilding %s because missing" % outnm
            return 1
        if name != self.name:
            print "rebuilding %s because name changed" % outnm
            return 1
        if level != self.level:
            print "rebuilding %s because level changed" % outnm
            return 1
        if toc != self.toc:
            print "rebuilding %s because toc changed" % outnm
            return 1
        for (nm, fnm, typ) in toc:
            if mtime(fnm) > last_build:
                print "rebuilding %s because %s changed" % (outnm, fnm)
                return 1
            if fnm[-1] in ('c', 'o'):
                if mtime(fnm[:-1]) > last_build:
                    print "rebuilding %s because %s changed" % (outnm, fnm[:-1])
                    return 1
        return 0
    def assemble(self):
        print "building PYZ", os.path.basename(self.out)
        pyz = archive.ZlibArchive(level=self.level)
        toc = self.toc - config['PYZ_dependencies']
        for (nm, fnm, typ) in toc:
            if mtime(fnm[:-1]) > mtime(fnm):
                py_compile.compile(fnm[:-1])
        pyz.build(self.name, toc)
        outf = open(self.out, 'w')
        pprint.pprint((self.name, self.level, self.toc), outf)
        outf.close()
        return 1

def checkCache(fnm, strip, upx):
    if not strip and not upx:
        return fnm
    if strip:
        strip = 1
    else:
        strip = 0
    if upx:
        upx = 1
    else:
        upx = 0
    cachedir = os.path.join(HOMEPATH, 'bincache%d%d' %  (strip, upx))
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)
    basenm = os.path.basename(fnm)
    cachedfile = os.path.join(cachedir, basenm )
    if os.path.exists(cachedfile):
        if mtime(fnm) > mtime(cachedfile):
            os.remove(cachedfile)
        else:
            return cachedfile
    if upx:
        if strip:
            fnm = checkCache(fnm, 1, 0)
        cmd = "upx --best -q \"%s\"" % cachedfile
    else:
        cmd = "strip \"%s\"" % cachedfile
    shutil.copy2(fnm, cachedfile)
    os.chmod(cachedfile, 0755)
    os.system(cmd)
    return cachedfile

UNCOMPRESSED, COMPRESSED = range(2)
class PKG(Target):
    typ = 'PKG'
    xformdict = {'PYMODULE' : 'm',
                 'PYSOURCE' : 's',
                 'EXTENSION' : 'b',
                 'PYZ' : 'z',
                 'PKG' : 'a',
                 'DATA': 'x',
                 'BINARY': 'b',
                 'EXECUTABLE': 'b'}
    def __init__(self, toc, name=None, cdict=None, exclude_binaries=0,
                 strip_binaries=0, upx_binaries=0):
        Target.__init__(self)
        self.toc = toc
        self.cdict = cdict
        self.name = name
        self.exclude_binaries = exclude_binaries
        self.strip_binaries = strip_binaries
        self.upx_binaries = upx_binaries
        if name is None:
            self.name = self.out[:-3] + 'pkg'
        if self.cdict is None:
            if config['useZLIB']:
                self.cdict = {'EXTENSION':COMPRESSED,
                              'DATA':COMPRESSED,
                              'BINARY':COMPRESSED,
                              'EXECUTABLE':COMPRESSED,
                              'PYSOURCE':COMPRESSED,
                              'PYMODULE':COMPRESSED }
            else:
                self.cdict = { 'PYSOURCE':UNCOMPRESSED }
        self.__postinit__()
    def check_guts(self, last_build):
        outnm = os.path.basename(self.out)
        if not os.path.exists(self.name):
            print "rebuilding %s because %s is missing" % (outnm, os.path.basename(self.name))
            return 1
        try:
            name, cdict, toc, exclude_binaries, strip_binaries, upx_binaries = eval(open(self.out, 'r').read())
        except:
            print "rebuilding %s because %s is missing" % (outnm, outnm)
            return 1
        if name != self.name:
            print "rebuilding %s because name changed" % outnm
            return 1
        if cdict != self.cdict:
            print "rebuilding %s because cdict changed" % outnm
            return 1
        if toc != self.toc:
            print "rebuilding %s because toc changed" % outnm
            return 1
        if exclude_binaries != self.exclude_binaries:
            print "rebuilding %s because exclude_binaries changed" % outnm
            return 1
        if strip_binaries != self.strip_binaries:
            print "rebuilding %s because strip_binaries changed" % outnm
            return 1
        if upx_binaries != self.upx_binaries:
            print "rebuilding %s because upx_binaries changed" % outnm
            return 1
        for (nm, fnm, typ) in toc:
            if mtime(fnm) > last_build:
                print "rebuilding %s because %s changed" % (outnm, fnm)
                return 1
        return 0
    def assemble(self):
        print "building PKG", os.path.basename(self.name)
        trash = []
        mytoc = []
        toc = TOC()
        for item in self.toc:
            inm, fnm, typ = item
            if typ == 'EXTENSION':
                binext = os.path.splitext(fnm)[1]
                if not os.path.splitext(inm)[1] == binext:
                    inm = inm + binext
            toc.append((inm, fnm, typ))
        seen = {}
        for inm, fnm, typ in toc:
            if typ in ('BINARY', 'EXTENSION'):
                if self.exclude_binaries:
                    self.dependencies.append((inm, fnm, typ))
                else:
                    fnm = checkCache(fnm, self.strip_binaries,
                                     self.upx_binaries and ( iswin or cygwin )
                                      and config['hasUPX'])
                    # Avoid importing the same binary extension twice. This might
                    # happen if they come from different sources (eg. once from
                    # binary dependence, and once from direct import).
                    if typ == 'BINARY' and seen.has_key(fnm):
                        continue
                    seen[fnm] = 1
                    mytoc.append((inm, fnm, self.cdict.get(typ,0),
                                  self.xformdict.get(typ,'b')))
            elif typ == 'OPTION':
                mytoc.append((inm, '', 0, 'o'))
            else:
                mytoc.append((inm, fnm, self.cdict.get(typ,0), self.xformdict.get(typ,'b')))
        archive = carchive.CArchive()
        archive.build(self.name, mytoc)
        outf = open(self.out, 'w')
        pprint.pprint((self.name, self.cdict, self.toc, self.exclude_binaries, self.strip_binaries, self.upx_binaries), outf)
        outf.close()
        for item in trash:
            os.remove(item)
        return 1

class ELFEXE(Target):
    typ = 'EXECUTABLE'
    exclude_binaries = 0
    def __init__(self, *args, **kws):
        Target.__init__(self)
        self.console = kws.get('console',1)
        self.debug = kws.get('debug',0)
        self.name = kws.get('name',None)
        self.icon = kws.get('icon',None)
        self.versrsrc = kws.get('version',None)
        self.strip = kws.get('strip',None)
        self.upx = kws.get('upx',None)
        self.exclude_binaries = kws.get('exclude_binaries',0)
        if self.name is None:
            self.name = self.out[:-3] + 'exe'
        if not os.path.isabs(self.name):
            self.name = os.path.join(SPECPATH, self.name)
        self.toc = TOC()
        for arg in args:
            if isinstance(arg, TOC):
                self.toc.extend(arg)
            elif isinstance(arg, Target):
                self.toc.append((os.path.basename(arg.name), arg.name, arg.typ))
                self.toc.extend(arg.dependencies)
            else:
                self.toc.extend(arg)
        self.toc.extend(config['EXE_dependencies'])
        self.pkg = PKG(self.toc, cdict=kws.get('cdict',None), exclude_binaries=self.exclude_binaries,
                       strip_binaries=self.strip, upx_binaries=self.upx)
        self.dependencies = self.pkg.dependencies
        self.__postinit__()
    def check_guts(self, last_build):
        outnm = os.path.basename(self.out)
        if not os.path.exists(self.name):
            print "rebuilding %s because %s missing" % (outnm, os.path.basename(self.name))
            return 1
        try:
            name, console, debug, icon, versrsrc, strip, upx, mtm = eval(open(self.out, 'r').read())
        except:
            print "rebuilding %s because %s missing or bad" % (outnm, outnm)
            return 1
        if name != self.name:
            print "rebuilding %s because name changed" % outnm
            return 1
        if console != self.console:
            print "rebuilding %s because console option changed" % outnm
            return 1
        if debug != self.debug:
            print "rebuilding %s because debug option changed" % outnm
            return 1
        if config['hasRsrcUpdate']:
            if icon != self.icon:
                print "rebuilding %s because icon option changed" % outnm
                return 1
            if versrsrc != self.versrsrc:
                print "rebuilding %s because versrsrc option changed" % outnm
                return 1
        else:
            if icon or versrsrc:
                print "ignoring icon and version resources = platform not capable"
        if strip != self.strip:
            print "rebuilding %s because strip option changed" % outnm
            return 1
        if upx != self.upx:
            print "rebuilding %s because upx option changed" % outnm
            return 1
        if mtm != mtime(self.name):
            print "rebuilding %s because mtimes don't match" % outnm
            return 1
        if mtm < mtime(self.pkg.out):
            print "rebuilding %s because pkg is more recent" % outnm
            return 1
        return 0
    def _bootloader_postfix(self, exe):
        if iswin:
            exe = exe + "_"
            is24 = hasattr(sys, "version_info") and sys.version_info[:2] >= (2,4)
            exe = exe + "67"[is24]
            exe = exe + "rd"[self.debug]
            exe = exe + "wc"[self.console]
        else:
            if not self.console:
                exe = exe + 'w'
            if self.debug:
                exe = exe + '_d'
        return exe
    def assemble(self):
        print "building ELFEXE", os.path.basename(self.out)
        trash = []
        outf = open(self.name, 'wb')
        exe = self._bootloader_postfix('support/loader/run')
        exe = os.path.join(HOMEPATH, exe)
        if iswin or cygwin:
            exe = exe + '.exe'
        if config['hasRsrcUpdate']:
            if self.icon:
                tmpnm = tempfile.mktemp()
                shutil.copy2(exe, tmpnm)
                os.chmod(tmpnm, 0755)
                icon.CopyIcons(tmpnm, self.icon)
                trash.append(tmpnm)
                exe = tmpnm
            if self.versrsrc:
                tmpnm = tempfile.mktemp()
                shutil.copy2(exe, tmpnm)
                os.chmod(tmpnm, 0755)
                versionInfo.SetVersion(tmpnm, self.versrsrc)
                trash.append(tmpnm)
                exe = tmpnm
        exe = checkCache(exe, self.strip, self.upx and config['hasUPX'])
        self.copy(exe, outf)
        self.copy(self.pkg.name, outf)
        outf.close()
        os.chmod(self.name, 0755)
        f = open(self.out, 'w')
        pprint.pprint((self.name, self.console, self.debug, self.icon, self.versrsrc,
                       self.strip, self.upx, mtime(self.name)), f)
        f.close()
        for item in trash:
            os.remove(item)
        return 1
    def copy(self, fnm, outf):
        inf = open(fnm, 'rb')
        while 1:
            data = inf.read(64*1024)
            if not data:
                break
            outf.write(data)

class DLL(ELFEXE):
    def assemble(self):
        print "building DLL", os.path.basename(self.out)
        outf = open(self.name, 'wb')
        dll = self._bootloader_postfix('support/loader/inprocsrvr')
        dll = os.path.join(HOMEPATH, dll)  + '.dll'
        self.copy(dll, outf)
        self.copy(self.pkg.name, outf)
        outf.close()
        os.chmod(self.name, 0755)
        f = open(self.out, 'w')
        pprint.pprint((self.name, self.console, self.debug, self.icon, self.versrsrc,
                       self.strip, self.upx, mtime(self.name)), f)
        f.close()
        return 1

class NonELFEXE(ELFEXE):
    def assemble(self):
        print "building NonELFEXE", os.path.basename(self.out)
        trash = []
        exe = 'support/loader/run'
        if not self.console:
            exe = exe + 'w'
        if self.debug:
            exe = exe + '_d'
        exe = os.path.join(HOMEPATH, exe)
        exe = checkCache(exe, self.strip, self.upx and config['hasUPX'])
        shutil.copy2(exe, self.name)
        os.chmod(self.name, 0755)
        shutil.copy2(self.pkg.name, self.name+'.pkg')
        f = open(self.out, 'w')
        pprint.pprint((self.name, self.console, self.debug, self.icon, self.versrsrc,
                       self.strip, self.upx, mtime(self.name)), f)
        f.close()
        for fnm in trash:
            os.remove(fnm)
        return 1

if config['useELFEXE']:
    EXE = ELFEXE
else:
    EXE = NonELFEXE

class COLLECT(Target):
    def __init__(self, *args, **kws):
        Target.__init__(self)
        self.name = kws.get('name',None)
        if self.name is None:
            self.name = 'dist_' + self.out[:-4]
        self.strip_binaries = kws.get('strip',0)
        self.upx_binaries = kws.get('upx',0)
        if not os.path.isabs(self.name):
            self.name = os.path.join(SPECPATH, self.name)
        self.toc = TOC()
        for arg in args:
            if isinstance(arg, TOC):
                self.toc.extend(arg)
            elif isinstance(arg, Target):
                self.toc.append((os.path.basename(arg.name), arg.name, arg.typ))
                if isinstance(arg, NonELFEXE):
                    self.toc.append((os.path.basename(arg.name)+'.pkg', arg.name+'.pkg', 'PKG'))
                self.toc.extend(arg.dependencies)
            else:
                self.toc.extend(arg)
        self.__postinit__()
    def check_guts(self, last_build):
        outnm = os.path.basename(self.out)
        try:
            name, strip_binaries, upx_binaries, toc = eval(open(self.out, 'r').read())
        except:
            print "building %s because %s missing" % (outnm, outnm)
            return 1
        if name != self.name:
            print "building %s because name changed" % outnm
            return 1
        if strip_binaries != self.strip_binaries:
            print "building %s because strip_binaries option changed" % outnm
            return 1
        if upx_binaries != self.upx_binaries:
            print "building %s because upx_binaries option changed" % outnm
            return 1
        if toc != self.toc:
            print "building %s because toc changed" % outnm
            return 1
        for inm, fnm, typ in self.toc:
            if typ == 'EXTENSION':
                ext = os.path.splitext(fnm)[1]
                test = os.path.join(self.name, inm+ext)
            else:
                test = os.path.join(self.name, os.path.basename(fnm))
            if not os.path.exists(test):
                print "building %s because %s is missing" % (outnm, test)
                return 1
            if mtime(fnm) > mtime(test):
                print "building %s because %s is more recent" % (outnm, fnm)
                return 1
        return 0
    def assemble(self):
        print "building COLLECT", os.path.basename(self.out)
        if not os.path.exists(self.name):
            os.mkdir(self.name)
        toc = TOC()
        for inm, fnm, typ in self.toc:
            if typ == 'EXTENSION':
                binext = os.path.splitext(fnm)[1]
                if not os.path.splitext(inm)[1] == binext:
                    inm = inm + binext
            toc.append((inm, fnm, typ))
        for inm, fnm, typ in toc:
            tofnm = os.path.join(self.name, inm)
            todir = os.path.dirname(tofnm)
            if not os.path.exists(todir):
                os.makedirs(todir)
            if typ in ('EXTENSION', 'BINARY'):
                fnm = checkCache(fnm, self.strip_binaries,
                                 self.upx_binaries and ( iswin or cygwin )
                                  and config['hasUPX'])
            shutil.copy2(fnm, tofnm)
            if typ in ('EXTENSION', 'BINARY'):
                os.chmod(tofnm, 0755)
        f = open(self.out, 'w')
        pprint.pprint((self.name, self.strip_binaries, self.upx_binaries, self.toc), f)
        f.close()
        return 1

import UserList
class TOC(UserList.UserList):
    def __init__(self, initlist=None):
        UserList.UserList.__init__(self)
        self.fltr = {}
        if initlist:
            for tpl in initlist:
                self.append(tpl)
    def append(self, tpl):
        try:
            if not self.fltr.get(tpl[0]):
                self.data.append(tpl)
                self.fltr[tpl[0]] = 1
        except TypeError:
            print "TOC found a %s, not a tuple" % tpl
            raise
    def insert(self, pos, tpl):
        if not self.fltr.get(tpl[0]):
            self.data.insert(pos, tpl)
            self.fltr[tpl[0]] = 1
    def __add__(self, other):
        rslt = TOC(self.data)
        rslt.extend(other)
        return rslt
    def __radd__(self, other):
        rslt = TOC(other)
        rslt.extend(self.data)
        return rslt
    def extend(self, other):
        for tpl in other:
            self.append(tpl)
    def __sub__(self, other):
        fd = self.fltr.copy()
        # remove from fd if it's in other
        for tpl in other:
            if fd.get(tpl[0],0):
                del fd[tpl[0]]
        rslt = TOC()
        # return only those things still in fd (preserve order)
        for tpl in self.data:
            if fd.get(tpl[0],0):
                rslt.append(tpl)
        return rslt
    def __rsub__(self, other):
        rslt = TOC(other)
        return rslt.__sub__(self)
    def intersect(self, other):
        rslt = TOC()
        for tpl in other:
            if self.fltr.get(tpl[0],0):
                rslt.append(tpl)
        return rslt

class Tree(Target, TOC):
    def __init__(self, root=None, prefix=None, excludes=None):
        Target.__init__(self)
        TOC.__init__(self)
        self.root = root
        self.prefix = prefix
        self.excludes = excludes
        if excludes is None:
            self.excludes = []
        self.__postinit__()
    def check_guts(self, last_build):
        outnm = os.path.basename(self.out)
        try:
            root, prefix, excludes, toc = eval(open(self.out, 'r').read())
        except:
            print "building %s because %s is missing / bad" % (outnm, outnm)
            return 1
        if root != self.root:
            print "building %s because root changed" % outnm
            return 1
        if prefix != self.prefix:
            print "building %s because prefix changed" % outnm
            return 1
        if excludes != self.excludes:
            print "building %s because excludes changed" % outnm
            return 1
        stack = [root]
        while stack:
            d = stack.pop()
            if mtime(d) > last_build:
                print "building %s because directory %s changed" % (outnm, d)
                return 1
            for nm in os.listdir(d):
                path = os.path.join(d, nm)
                if os.path.isdir(path):
                    stack.append(path)
        self.data = toc
        return 0
    def assemble(self):
        print "building Tree", os.path.basename(self.out)
        stack = [(self.root, self.prefix)]
        excludes = {}
        xexcludes = {}
        for nm in self.excludes:
            if nm[0] == '*':
                xexcludes[nm[1:]] = 1
            else:
                excludes[nm] = 1
        rslt = []
        while stack:
            dir, prefix = stack.pop()
            for fnm in os.listdir(dir):
                if excludes.get(fnm, 0) == 0:
                    ext = os.path.splitext(fnm)[1]
                    if xexcludes.get(ext,0) == 0:
                        fullfnm = os.path.join(dir, fnm)
                        rfnm = prefix and os.path.join(prefix, fnm) or fnm
                        if os.path.isdir(fullfnm):
                            stack.append((fullfnm, rfnm))
                        else:
                            rslt.append((rfnm, fullfnm, 'DATA'))
        try:
            oldstuff = eval(open(self.out, 'r').read())
        except:
            oldstuff = None
        if oldstuff != (self.root, self.prefix, self.excludes, rslt):
            outf = open(self.out, 'w')
            pprint.pprint((self.root, self.prefix, self.excludes, rslt), outf)
            outf.close()
            self.data = rslt
            return 1
        print self.out, "no change!"
        return 0

def TkTree():
    tclroot = config['TCL_root']
    tclnm = os.path.join('_MEI', os.path.basename(tclroot))
    tkroot = config['TK_root']
    tknm = os.path.join('_MEI', os.path.basename(tkroot))
    tcltree = Tree(tclroot, tclnm, excludes=['demos','encoding','*.lib'])
    tktree = Tree(tkroot, tknm, excludes=['demos','encoding','*.lib'])
    return tcltree + tktree

def TkPKG():
    return PKG(TkTree(), name='tk.pkg')

usage = """\
Usage: python %s <specfile>

See doc/Tutorial.html for details.
"""

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print usage % sys.argv[0]
    else:
        build(sys.argv[1])




