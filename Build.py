#!/usr/bin/env python
#
# Build packages using spec files
#
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

import sys
import os
import shutil
import pprint
import time
import py_compile
import tempfile
try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5
import UserList
import mf
import archive
import iu
import carchive
import bindepend
import traceback

STRINGTYPE = type('')
TUPLETYPE = type((None,))
UNCOMPRESSED, COMPRESSED = range(2)

# todo: use pkg_resources here
HOMEPATH = os.path.dirname(sys.argv[0])
SPEC = None
SPECPATH = None
BUILDPATH = None
WARNFILE = None

rthooks = {}
iswin = sys.platform[:3] == 'win'
cygwin = sys.platform == 'cygwin'

def system(cmd):
    # This workaround is required because NT shell doesn't work with commands
    # that start with double quotes (required if there are spaces inside the
    # command path)
    if iswin:
        cmd = 'echo on && ' + cmd
    os.system(cmd)

def _save_data(filename, data):
    outf = open(filename, 'w')
    pprint.pprint(data, outf)
    outf.close()

def _load_data(filename):
    return eval(open(filename, 'r').read().replace("\r\n","\n"))

def setupUPXFlags():
    f = os.environ.get("UPX", "")
    is24 = hasattr(sys, "version_info") and sys.version_info[:2] >= (2,4)
    if iswin and is24:
        # Binaries built with Visual Studio 7.1 require --strip-loadconf
        # or they won't compress. Configure.py makes sure that UPX is new
        # enough to support --strip-loadconf.
        f = "--strip-loadconf " + f
    # Do not compress any icon, so that additional icons in the executable
    # can still be externally bound
    f = "--compress-icons=0 " + f
    f = "--best " + f
    os.environ["UPX"] = f

def mtime(fnm):
    try:
        return os.stat(fnm)[8]
    except:
        return 0

def absnormpath(apath):
    return os.path.abspath(os.path.normpath(apath))

def compile_pycos(toc):
    """Given a TOC or equivalent list of tuples, generates all the required
    pyc/pyo files, writing in a local directory if required, and returns the
    list of tuples with the updated pathnames.
    """
    global BUILDPATH

    # For those modules that need to be rebuilt, use the build directory
    # PyInstaller creates during the build process.
    basepath = "/".join([BUILDPATH, "localpycos"])

    new_toc = []
    for (nm, fnm, typ) in toc:

        # Trim the terminal "c" or "o"
        source_fnm = fnm[:-1]

        # If the source is newer than the compiled, or the compiled doesn't
        # exist, we need to perform a build ourselves.
        if mtime(source_fnm) > mtime(fnm):
            try:
                py_compile.compile(source_fnm)
            except IOError:
                # If we're compiling on a system directory, probably we don't
                # have write permissions; thus we compile to a local directory
                # and change the TOC entry accordingly.
                ext = os.path.splitext(fnm)[1]

                if "__init__" not in fnm:
                    # If it's a normal module, use last part of the qualified
                    # name as module name and the first as leading path
                    leading, mod_name = nm.split(".")[:-1], nm.split(".")[-1]
                else:
                    # In case of a __init__ module, use all the qualified name
                    # as leading path and use "__init__" as the module name
                    leading, mod_name = nm.split("."), "__init__"

                leading.insert(0, basepath)
                leading = "/".join(leading)

                if not os.path.exists(leading):
                    os.makedirs(leading)

                fnm = "/".join([leading, mod_name + ext])
                py_compile.compile(source_fnm, fnm)

        new_toc.append((nm, fnm, typ))

    return new_toc

def addSuffixToExtensions(toc):
    """
    Returns a new TOC with proper library suffix for EXTENSION items.
    """
    new_toc = TOC()
    for inm, fnm, typ in toc:
        if typ == 'EXTENSION':
            binext = os.path.splitext(fnm)[1]
            if not os.path.splitext(inm)[1] == binext:
                inm = inm + binext
        new_toc.append((inm, fnm, typ))
    return new_toc

def architecture():
    """
    Returns the bit depth of the python interpreter's architecture as
    a string ('32bit' or '64bit'). Similar to platform.architecture(),
    but with fixes for universal binaries on MacOS.
    """
    if sys.platform == "darwin":
        # Darwin's platform.architecture() is buggy and always
        # returns "64bit" even for the 32bit version of Python's
        # universal binary. So we roll out our own (that works
        # on Darwin).
        if sys.maxint > 2L**32:
            return '64bit'
        else:
            return '32bit'

    # Python 2.3+
    import platform
    return platform.architecture()[0]


#--- functons for checking guts ---

def _check_guts_eq(attr, old, new, last_build):
    """
    rebuild is required if values differ
    """
    if old != new:
        print "building because %s changed" % attr
        return True
    return False

def _check_guts_toc_mtime(attr, old, toc, last_build, pyc=0):
    """
    rebuild is required if mtimes of files listed in old toc are newer
    than ast_build

    if pyc=1, check for .py files, too
    """
    for (nm, fnm, typ) in old:
        if mtime(fnm) > last_build:
            print "building because %s changed" % fnm
            return True
        elif pyc and mtime(fnm[:-1]) > last_build:
            print "building because %s changed" % fnm[:-1]
            return True
    return False

def _check_guts_toc(attr, old, toc, last_build, pyc=0):
    """
    rebuild is required if either toc content changed if mtimes of
    files listed in old toc are newer than ast_build

    if pyc=1, check for .py files, too
    """
    return    _check_guts_eq       (attr, old, toc, last_build) \
           or _check_guts_toc_mtime(attr, old, toc, last_build, pyc=pyc)

def _rmdir(path):
    """
    Remove dirname(os.path.abspath(path)) and all its contents, but only if:

    1. It doesn't start with BUILDPATH
    2. It is a directory and not empty (otherwise continue without removing
       the directory)
    3. BUILDPATH and SPECPATH don't start with it
    4. The --noconfirm option is set, or sys.stdout is a tty and the user
       confirms directory removal

    Otherwise, error out.
    """
    if not os.path.abspath(path):
        path = os.path.abspath(path)
    if not path.startswith(BUILDPATH) and os.path.isdir(path) and os.listdir(path):
        specerr = 0
        if BUILDPATH.startswith(path):
            print ('E: specfile error: The output path "%s" contains '
                   'BUILDPATH (%s)') % (path, BUILDPATH)
            specerr += 1
        if SPECPATH.startswith(path):
            print ('E: Specfile error: The output path "%s" contains '
                   'SPECPATH (%s)') % (path, SPECPATH)
            specerr += 1
        if specerr:
            print ('Please edit/recreate the specfile (%s), set a different '
                   'output name (e.g. "dist") and run Build.py again.') % SPEC
            sys.exit(1)
        if opts.noconfirm:
            choice = 'y'
        elif sys.stdout.isatty():
            choice = raw_input('WARNING: The output directory "%s" and ALL ITS '
                               'CONTENTS will be REMOVED! Continue? (y/n)' % path)
        else:
            print ('E: The output directory "%s" is not empty. Please remove '
                   'all its contents and run Build.py again, or use Build.py '
                   '-y (remove output directory without confirmation).') % path
            sys.exit(1)
        if choice.strip().lower() == 'y':
            print 'I: Removing', path
            shutil.rmtree(path)
        else:
            print 'I: User aborted'
            sys.exit(1)

def check_egg(pth):
    """Check if path points to a file inside a python egg file (or to an egg
       directly)."""
    if sys.version_info >= (2,3):
        if os.path.altsep:
            pth = pth.replace(os.path.altsep, os.path.sep)
        components = pth.split(os.path.sep)
        sep = os.path.sep
    else:
        components = pth.replace("\\", "/").split("/")
        sep = "/"
        if iswin:
            sep = "\\"
    for i,name in zip(range(0,len(components)), components):
        if name.lower().endswith(".egg"):
            eggpth = sep.join(components[:i + 1])
            if os.path.isfile(eggpth):
                # eggs can also be directories!
                return True
    return False

#--

class Target:
    invcnum = 0
    def __init__(self):
        self.invcnum = Target.invcnum
        Target.invcnum += 1
        self.out = os.path.join(BUILDPATH, 'out%s%d.toc' % (self.__class__.__name__,
                                                            self.invcnum))
        self.outnm = os.path.basename(self.out)
        self.dependencies = TOC()

    def __postinit__(self):
        print "checking %s" % (self.__class__.__name__,)
        if self.check_guts(mtime(self.out)):
            self.assemble()

    GUTS = []

    def check_guts(self, last_build):
        pass

    def get_guts(self, last_build, missing ='missing or bad'):
        """
        returns None if guts have changed
        """
        try:
            data = _load_data(self.out)
        except:
            print "building because", os.path.basename(self.out), missing
            return None

        if len(data) != len(self.GUTS):
            print "building because %s is bad" % self.outnm
            return None
        for i in range(len(self.GUTS)):
            attr, func = self.GUTS[i]
            if func is None:
                # no check for this value
                continue
            if func(attr, data[i], getattr(self, attr), last_build):
                return None
        return data


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
                self.pathex.append(absnormpath(path))
        sys.pathex = self.pathex[:]
        self.hookspath = hookspath
        self.excludes = excludes
        self.scripts = TOC()
        self.pure = TOC()
        self.binaries = TOC()
        self.zipfiles = TOC()
        self.datas = TOC()
        self.__postinit__()

    GUTS = (('inputs',    _check_guts_eq),
            ('pathex',    _check_guts_eq),
            ('hookspath', _check_guts_eq),
            ('excludes',  _check_guts_eq),
            ('scripts',   _check_guts_toc_mtime),
            ('pure',      lambda *args: apply(_check_guts_toc_mtime,
                                              args, {'pyc': 1 }   )),
            ('binaries',  _check_guts_toc_mtime),
            ('zipfiles',  _check_guts_toc_mtime),
            ('datas',     _check_guts_toc_mtime),
            )

    def check_guts(self, last_build):
        if last_build == 0:
            print "building %s because %s non existent" % (self.__class__.__name__, self.outnm)
            return True
        for fnm in self.inputs:
            if mtime(fnm) > last_build:
                print "building because %s changed" % fnm
                return True

        data = Target.get_guts(self, last_build)
        if not data:
            return True
        scripts, pure, binaries, zipfiles, datas = data[-5:]
        self.scripts = TOC(scripts)
        self.pure = TOC(pure)
        self.binaries = TOC(binaries)
        self.zipfiles = TOC(zipfiles)
        self.datas = TOC(datas)
        return False

    def assemble(self):
        print "running Analysis", os.path.basename(self.out)
        # Reset seen variable to correctly discover dependencies
        # if there are multiple Analysis in a single specfile.
        bindepend.seen = {}

        paths = self.pathex
        for i in range(len(paths)):
            # FIXME: isn't self.pathex already norm-abs-pathed?
            paths[i] = absnormpath(paths[i])
        ###################################################
        # Scan inputs and prepare:
        dirs = {}  # input directories
        pynms = [] # python filenames with no extension
        for script in self.inputs:
            if not os.path.exists(script):
                print "Analysis: script %s not found!" % script
                sys.exit(1)
            d, base = os.path.split(script)
            if not d:
                d = os.getcwd()
            d = absnormpath(d)
            pynm, ext = os.path.splitext(base)
            dirs[d] = 1
            pynms.append(pynm)
        ###################################################
        # Initialize analyzer and analyze scripts
        analyzer = mf.ImportTracker(dirs.keys()+paths, self.hookspath,
                                    self.excludes,
                                    target_platform=target_platform)
        #print analyzer.path
        scripts = [] # will contain scripts to bundle
        for i in range(len(self.inputs)):
            script = self.inputs[i]
            print "Analyzing:", script
            analyzer.analyze_script(script)
            scripts.append((pynms[i], script, 'PYSOURCE'))
        ###################################################
        # Fills pure, binaries and rthookcs lists to TOC
        pure = []     # pure python modules
        binaries = [] # binaries to bundle
        zipfiles = [] # zipfiles to bundle
        datas = []    # datafiles to bundle
        rthooks = []  # rthooks if needed
        for modnm, mod in analyzer.modules.items():
            # FIXME: why can we have a mod == None here?
            if mod is not None:
                hooks = findRTHook(modnm)  #XXX
                if hooks:
                    rthooks.extend(hooks)
                datas.extend(mod.datas)
                if isinstance(mod, mf.BuiltinModule):
                    pass
                else:
                    fnm = mod.__file__
                    if isinstance(mod, mf.ExtensionModule):
                        binaries.append((mod.__name__, fnm, 'EXTENSION'))
                    elif isinstance(mod, (mf.PkgInZipModule, mf.PyInZipModule)):
                        zipfiles.append(("eggs/" + os.path.basename(str(mod.owner)),
                                         str(mod.owner), 'ZIPFILE'))
                    else:
                        # mf.PyModule instances expose a list of binary
                        # dependencies, most probably shared libraries accessed
                        # via ctypes. Add them to the overall required binaries.
                        binaries.extend(mod.binaries)
                        if modnm != '__main__':
                            pure.append((modnm, fnm, 'PYMODULE'))
        # Always add python's dependencies first
        # This ensures that assembly depencies under Windows get pulled in
        # first and we do not need to add assembly DLLs to the exclude list
        # explicitly
        python = config['python']
        if not iswin:
            while os.path.islink(python):
                python = os.path.join(os.path.split(python)[0], os.readlink(python))
            depmanifest = None
        else:
            depmanifest = winmanifest.Manifest(type_="win32", name=specnm,
                                               processorArchitecture="x86",
                                               version=(1, 0, 0, 0))
            depmanifest.filename = os.path.join(BUILDPATH,
                                                specnm + ".exe.manifest")
        binaries.extend(bindepend.Dependencies([('', python, '')],
                                               target_platform,
                                               config['xtrapath'],
                                               manifest=depmanifest)[1:])
        binaries.extend(bindepend.Dependencies(binaries,
                                               platform=target_platform,
                                               manifest=depmanifest))
        if iswin:
            depmanifest.writeprettyxml()
        self.fixMissingPythonLib(binaries)
        if zipfiles:
            scripts[-1:-1] = [("_pyi_egg_install.py", os.path.join(HOMEPATH, "support/_pyi_egg_install.py"), 'PYSOURCE')]
        # Add realtime hooks just before the last script (which is
        # the entrypoint of the application).
        scripts[-1:-1] = rthooks
        self.scripts = TOC(scripts)
        self.pure = TOC(pure)
        self.binaries = TOC(binaries)
        self.zipfiles = TOC(zipfiles)
        self.datas = TOC(datas)
        try: # read .toc
            oldstuff = _load_data(self.out)
        except:
            oldstuff = None

        self.pure = TOC(compile_pycos(self.pure))

        newstuff = (self.inputs, self.pathex, self.hookspath, self.excludes,
                    self.scripts, self.pure, self.binaries, self.zipfiles, self.datas)
        if oldstuff != newstuff:
            _save_data(self.out, newstuff)
            wf = open(WARNFILE, 'w')
            for ln in analyzer.getwarnings():
                wf.write(ln+'\n')
            wf.close()
            print "Warnings written to %s" % WARNFILE
            return 1
        print self.out, "no change!"
        return 0

    def fixMissingPythonLib(self, binaries):
        """Add the Python library if missing from the binaries.

        Some linux distributions (e.g. debian-based) statically build the
        Python executable to the libpython, so bindepend doesn't include
        it in its output.

        Darwin custom builds could possibly also have non-framework style libraries, 
        so this method also checks for that variant as well.
        """

        if target_platform.startswith("linux"):
            names = ('libpython%d.%d.so' % sys.version_info[:2],) 
        elif target_platform.startswith("darwin"):
            names = ('Python', 'libpython%d.%d.dylib' % sys.version_info[:2])
        else:
            return

        for (nm, fnm, typ) in binaries:
            for name in names: 
                if typ == 'BINARY' and name in fnm:
                    # lib found
                    return

        # resume search using the first item in names
        name = names[0]

        if target_platform.startswith("linux"):
            lib = bindepend.findLibrary(name)
            if lib is None:
                raise IOError("Python library not found!")

        elif target_platform.startswith("darwin"):
            # On MacPython, Analysis.assemble is able to find the libpython with
            # no additional help, asking for config['python'] dependencies.
            # However, this fails on system python, because the shared library
            # is not listed as a dependency of the binary (most probably it's
            # opened at runtime using some dlopen trickery).
            lib = os.path.join(sys.exec_prefix, 'Python')
            if not os.path.exists(lib):
                raise IOError("Python library not found!")

        binaries.append((os.path.split(lib)[1], lib, 'BINARY'))


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
    def __init__(self, toc, name=None, level=9, crypt=None):
        Target.__init__(self)
        self.toc = toc
        self.name = name
        if name is None:
            self.name = self.out[:-3] + 'pyz'
        if config['useZLIB']:
            self.level = level
        else:
            self.level = 0
        if config['useCrypt'] and crypt is not None:
            self.crypt = archive.Keyfile(crypt).key
        else:
            self.crypt = None
        self.dependencies = compile_pycos(config['PYZ_dependencies'])
        self.__postinit__()

    GUTS = (('name',   _check_guts_eq),
            ('level',  _check_guts_eq),
            ('crypt',  _check_guts_eq),
            ('toc',    _check_guts_toc), # todo: pyc=1
            )

    def check_guts(self, last_build):
        _rmdir(self.name)
        if not os.path.exists(self.name):
            print "rebuilding %s because %s is missing" % (self.outnm, os.path.basename(self.name))
            return True

        data = Target.get_guts(self, last_build)
        if not data:
            return True
        return False

    def assemble(self):
        print "building PYZ", os.path.basename(self.out)
        pyz = archive.ZlibArchive(level=self.level, crypt=self.crypt)
        toc = self.toc - config['PYZ_dependencies']
        pyz.build(self.name, toc)
        _save_data(self.out, (self.name, self.level, self.crypt, self.toc))
        return 1

def cacheDigest(fnm):
    data = open(fnm, "rb").read()
    digest = md5(data).digest()
    return digest

def checkCache(fnm, strip, upx):
    # On darwin a cache is required anyway to keep the libaries
    # with relative install names
    if (not strip and not upx and sys.platform[:6] != 'darwin' and
        sys.platform != 'win32') or fnm.lower().endswith(".manifest"):
        return fnm
    if strip:
        strip = 1
    else:
        strip = 0
    if upx:
        upx = 1
    else:
        upx = 0

    # Load cache index
    cachedir = os.path.join(HOMEPATH, 'bincache%d%d' %  (strip, upx))
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)
    cacheindexfn = os.path.join(cachedir, "index.dat")
    if os.path.exists(cacheindexfn):
        cache_index = _load_data(cacheindexfn)
    else:
        cache_index = {}

    # Verify if the file we're looking for is present in the cache.
    basenm = os.path.normcase(os.path.basename(fnm))
    digest = cacheDigest(fnm)
    cachedfile = os.path.join(cachedir, basenm)
    cmd = None
    if cache_index.has_key(basenm):
        if digest != cache_index[basenm]:
            os.remove(cachedfile)
        else:
            return cachedfile
    if upx:
        if strip:
            fnm = checkCache(fnm, 1, 0)
        bestopt = "--best"
        # FIXME: Linux builds of UPX do not seem to contain LZMA (they assert out)
        # A better configure-time check is due.
        if config["hasUPX"] >= (3,) and os.name == "nt":
            bestopt = "--lzma"

        upx_executable = "upx"
        if config.get('upx_dir'):
            upx_executable = os.path.join(config['upx_dir'], upx_executable)
        cmd = '"' + upx_executable + '" ' + bestopt + " -q \"%s\"" % cachedfile
    else:
        if strip:
            # -S = strip only debug symbols.
            # The default strip behaviour breaks some shared libraries
            # under Mac OSX.
            cmd = "strip -S \"%s\"" % cachedfile
    shutil.copy2(fnm, cachedfile)
    os.chmod(cachedfile, 0755)

    if pyasm and fnm.lower().endswith(".pyd"):
        # If python.exe has dependent assemblies, check for embedded manifest
        # of cached pyd file because we may need to 'fix it' for pyinstaller
        try:
            res = winmanifest.GetManifestResources(os.path.abspath(cachedfile))
        except winresource.pywintypes.error, e:
            if e.args[0] == winresource.ERROR_BAD_EXE_FORMAT:
                # Not a win32 PE file
                pass
            else:
                print "E:", os.path.abspath(cachedfile)
                raise
        else:
            if winmanifest.RT_MANIFEST in res and len(res[winmanifest.RT_MANIFEST]):
                for name in res[winmanifest.RT_MANIFEST]:
                    for language in res[winmanifest.RT_MANIFEST][name]:
                        try:
                            manifest = winmanifest.Manifest()
                            manifest.filename = ":".join([cachedfile,
                                                          str(winmanifest.RT_MANIFEST),
                                                          str(name),
                                                          str(language)])
                            manifest.parse_string(res[winmanifest.RT_MANIFEST][name][language],
                                                  False)
                        except Exception, exc:
                            print ("E: Cannot parse manifest resource %s, "
                                   "%s from") % (name, language)
                            print "E:", cachedfile
                            print "E:", traceback.format_exc()
                        else:
                            # Fix the embedded manifest (if any):
                            # Extension modules built with Python 2.6.5 have
                            # an empty <dependency> element, we need to add
                            # dependentAssemblies from python.exe for
                            # pyinstaller
                            olen = len(manifest.dependentAssemblies)
                            for pydep in pyasm:
                                if not pydep.name in [dep.name for dep in
                                                      manifest.dependentAssemblies]:
                                    print ("Adding %s to dependent assemblies "
                                           "of %s") % (pydep.name, cachedfile)
                                    manifest.dependentAssemblies.append(pydep)
                            if len(manifest.dependentAssemblies) > olen:
                                try:
                                    manifest.update_resources(os.path.abspath(cachedfile),
                                                              [name],
                                                              [language])
                                except Exception, e:
                                    print "E:", os.path.abspath(cachedfile)
                                    raise

    if cmd: system(cmd)

    # update cache index
    cache_index[basenm] = digest
    _save_data(cacheindexfn, cache_index)

    return cachedfile

UNCOMPRESSED, COMPRESSED, ENCRYPTED = range(3)
class PKG(Target):
    typ = 'PKG'
    xformdict = {'PYMODULE' : 'm',
                 'PYSOURCE' : 's',
                 'EXTENSION' : 'b',
                 'PYZ' : 'z',
                 'PKG' : 'a',
                 'DATA': 'x',
                 'BINARY': 'b',
                 'ZIPFILE': 'Z',
                 'EXECUTABLE': 'b'}
    def __init__(self, toc, name=None, cdict=None, exclude_binaries=0,
                 strip_binaries=0, upx_binaries=0, crypt=0):
        Target.__init__(self)
        self.toc = toc
        self.cdict = cdict
        self.name = name
        self.exclude_binaries = exclude_binaries
        self.strip_binaries = strip_binaries
        self.upx_binaries = upx_binaries
        self.crypt = crypt
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
                if self.crypt:
                    self.cdict['PYSOURCE'] = ENCRYPTED
                    self.cdict['PYMODULE'] = ENCRYPTED
            else:
                self.cdict = { 'PYSOURCE':UNCOMPRESSED }
        self.__postinit__()

    GUTS = (('name',   _check_guts_eq),
            ('cdict',  _check_guts_eq),
            ('toc',    _check_guts_toc_mtime),
            ('exclude_binaries',  _check_guts_eq),
            ('strip_binaries',  _check_guts_eq),
            ('upx_binaries',  _check_guts_eq),
            ('crypt', _check_guts_eq),
            )

    def check_guts(self, last_build):
        _rmdir(self.name)
        if not os.path.exists(self.name):
            print "rebuilding %s because %s is missing" % (self.outnm, os.path.basename(self.name))
            return 1

        data = Target.get_guts(self, last_build)
        if not data:
            return True
        # todo: toc equal
        return False


    def assemble(self):
        print "building PKG", os.path.basename(self.name)
        trash = []
        mytoc = []
        seen = {}
        toc = addSuffixToExtensions(self.toc)
        for inm, fnm, typ in toc:
            if not os.path.isfile(fnm) and check_egg(fnm):
                # file is contained within python egg, it is added with the egg
                continue
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
        _save_data(self.out,
                   (self.name, self.cdict, self.toc, self.exclude_binaries,
                    self.strip_binaries, self.upx_binaries, self.crypt))
        for item in trash:
            os.remove(item)
        return 1

class EXE(Target):
    typ = 'EXECUTABLE'
    exclude_binaries = 0
    append_pkg = 1
    def __init__(self, *args, **kws):
        Target.__init__(self)
        self.console = kws.get('console',1)
        self.debug = kws.get('debug',0)
        self.name = kws.get('name',None)
        self.icon = kws.get('icon',None)
        self.versrsrc = kws.get('version',None)
        self.manifest = kws.get('manifest',None)
        self.resources = kws.get('resources',[])
        self.strip = kws.get('strip',None)
        self.upx = kws.get('upx',None)
        self.crypt = kws.get('crypt', 0)
        self.exclude_binaries = kws.get('exclude_binaries',0)
        self.append_pkg = kws.get('append_pkg', self.append_pkg)
        if self.name is None:
            self.name = self.out[:-3] + 'exe'
        if not os.path.isabs(self.name):
            self.name = os.path.join(SPECPATH, self.name)
        if target_iswin or cygwin:
            self.pkgname = self.name[:-3] + 'pkg'
        else:
            self.pkgname = self.name + '.pkg'
        self.toc = TOC()
        for arg in args:
            if isinstance(arg, TOC):
                self.toc.extend(arg)
            elif isinstance(arg, Target):
                self.toc.append((os.path.basename(arg.name), arg.name, arg.typ))
                self.toc.extend(arg.dependencies)
            else:
                self.toc.extend(arg)
        if iswin:
            if sys.version[:3] == '1.5':
                import exceptions
                toc.append((os.path.basename(exceptions.__file__), exceptions.__file__, 'BINARY'))
            if self.manifest:
                if isinstance(self.manifest, basestring) and "<" in self.manifest:
                    # Assume XML string
                    self.manifest = winmanifest.ManifestFromXML(self.manifest)
                elif not isinstance(self.manifest, winmanifest.Manifest):
                    # Assume filename
                    self.manifest = winmanifest.ManifestFromXMLFile(self.manifest)
            else:
                self.manifest = winmanifest.ManifestFromXMLFile(os.path.join(BUILDPATH,
                                                                             specnm + ".exe.manifest"))
                self.manifest.name = os.path.splitext(os.path.basename(self.name))[0]
            if self.manifest.filename != os.path.join(BUILDPATH,
                                                      specnm + ".exe.manifest"):
                # Update dependent assemblies
                depmanifest = winmanifest.ManifestFromXMLFile(os.path.join(BUILDPATH,
                                                                           specnm + ".exe.manifest"))
                for assembly in depmanifest.dependentAssemblies:
                    if not assembly.name in [dependentAssembly.name
                                             for dependentAssembly in
                                             self.manifest.dependentAssemblies]:
                        self.manifest.dependentAssemblies.append(assembly)
            if not self.console and \
               not "Microsoft.Windows.Common-Controls" in [dependentAssembly.name
                                                           for dependentAssembly in
                                                           self.manifest.dependentAssemblies]:
                # Add Microsoft.Windows.Common-Controls to dependent assemblies
                self.manifest.dependentAssemblies.append(winmanifest.Manifest(type_="win32",
                                                                              name="Microsoft.Windows.Common-Controls",
                                                                              language="*",
                                                                              processorArchitecture="x86",
                                                                              version=(6, 0, 0, 0),
                                                                              publicKeyToken="6595b64144ccf1df"))
            self.manifest.writeprettyxml(os.path.join(BUILDPATH,
                                                      specnm + ".exe.manifest"))
            self.toc.append((os.path.basename(self.name) + ".manifest",
                             os.path.join(BUILDPATH,
                                          specnm + ".exe.manifest"),
                             'BINARY'))
        self.pkg = PKG(self.toc, cdict=kws.get('cdict',None), exclude_binaries=self.exclude_binaries,
                       strip_binaries=self.strip, upx_binaries=self.upx, crypt=self.crypt)
        self.dependencies = self.pkg.dependencies
        self.__postinit__()

    GUTS = (('name',     _check_guts_eq),
            ('console',  _check_guts_eq),
            ('debug',    _check_guts_eq),
            ('icon',     _check_guts_eq),
            ('versrsrc', _check_guts_eq),
            ('manifest', _check_guts_eq),
            ('resources', _check_guts_eq),
            ('strip',    _check_guts_eq),
            ('upx',      _check_guts_eq),
            ('crypt',    _check_guts_eq),
            ('mtm',      None,), # checked bellow
            )

    def check_guts(self, last_build):
        _rmdir(self.name)
        if not os.path.exists(self.name):
            print "rebuilding %s because %s missing" % (self.outnm, os.path.basename(self.name))
            return 1
        if not self.append_pkg and not os.path.exists(self.pkgname):
            print "rebuilding because %s missing" % (
                os.path.basename(self.pkgname),)
            return 1

        data = Target.get_guts(self, last_build)
        if not data:
            return True

        icon, versrsrc, manifest, resources = data[3:7]
        if (icon or versrsrc or manifest or resources) and not config['hasRsrcUpdate']:
            # todo: really ignore :-)
            print "ignoring icon, version, manifest and resources = platform not capable"

        mtm = data[-1]
        crypt = data[-2]
        if crypt != self.crypt:
            print "rebuilding %s because crypt option changed" % outnm
            return 1
        if mtm != mtime(self.name):
            print "rebuilding", self.outnm, "because mtimes don't match"
            return True
        if mtm < mtime(self.pkg.out):
            print "rebuilding", self.outnm, "because pkg is more recent"
            return True

        return False

    def _bootloader_file(self, exe):
        try:
            import platform
            # On some Windows installation (Python 2.4) platform.system() is
            # broken and incorrectly returns 'Microsoft' instead of 'Windows'.
            # http://mail.python.org/pipermail/patches/2007-June/022947.html
            syst = platform.system()
            syst_real = {'Microsoft': 'Windows'}.get(syst, syst)
            PLATFORM = syst_real + "-" + architecture()
        except ImportError:
            import os
            n = { "nt": "Windows", "linux2": "Linux", "darwin": "Darwin" }
            PLATFORM = n[os.name] + "-32bit"

        if not self.console:
            exe = exe + 'w'
        if self.debug:
            exe = exe + '_d'

        import os
        return os.path.join('support', 'loader', PLATFORM, exe)

    def assemble(self):
        print "building EXE from", os.path.basename(self.out)
        trash = []
        if not os.path.exists(os.path.dirname(self.name)):
            os.makedirs(os.path.dirname(self.name))
        outf = open(self.name, 'wb')
        exe = self._bootloader_file('run')
        exe = os.path.join(HOMEPATH, exe)
        if target_iswin or cygwin:
            exe = exe + '.exe'
        if config['hasRsrcUpdate'] and (self.icon or self.versrsrc or
                                        self.resources):
            tmpnm = tempfile.mktemp()
            shutil.copy2(exe, tmpnm)
            os.chmod(tmpnm, 0755)
            if self.icon:
                icon.CopyIcons(tmpnm, self.icon)
            if self.versrsrc:
                versionInfo.SetVersion(tmpnm, self.versrsrc)
            for res in self.resources:
                res = res.split(",")
                for i in range(len(res[1:])):
                    try:
                        res[i + 1] = int(res[i + 1])
                    except ValueError:
                        pass
                resfile = res[0]
                if len(res) > 1:
                    restype = res[1]
                else:
                    restype = None
                if len(res) > 2:
                    resname = res[2]
                else:
                    restype = None
                if len(res) > 3:
                    reslang = res[3]
                else:
                    restype = None
                try:
                    winresource.UpdateResourcesFromResFile(tmpnm, resfile,
                                                        [restype or "*"],
                                                        [resname or "*"],
                                                        [reslang or "*"])
                except winresource.pywintypes.error, exc:
                    if exc.args[0] != winresource.ERROR_BAD_EXE_FORMAT:
                        print "E:", str(exc)
                        continue
                    if not restype or not resname:
                        print "E: resource type and/or name not specified"
                        continue
                    if "*" in (restype, resname):
                        print ("E: no wildcards allowed for resource type "
                               "and name when source file does not contain "
                               "resources")
                        continue
                    try:
                        winresource.UpdateResourcesFromDataFile(tmpnm,
                                                             resfile,
                                                             restype,
                                                             [resname],
                                                             [reslang or 0])
                    except winresource.pywintypes.error, exc:
                        print "E:", str(exc)
            trash.append(tmpnm)
            exe = tmpnm
        exe = checkCache(exe, self.strip, self.upx and config['hasUPX'])
        self.copy(exe, outf)
        if self.append_pkg:
            print "Appending archive to EXE", self.name
            self.copy(self.pkg.name, outf)
        else:
            print "Copying archive to", self.pkgname
            shutil.copy2(self.pkg.name, self.pkgname)
        outf.close()
        os.chmod(self.name, 0755)
        _save_data(self.out,
                   (self.name, self.console, self.debug, self.icon,
                    self.versrsrc, self.resources, self.strip, self.upx, self.crypt, mtime(self.name)))
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

class DLL(EXE):
    def assemble(self):
        print "building DLL", os.path.basename(self.out)
        outf = open(self.name, 'wb')
        dll = self._bootloader_file('inprocsrvr')
        dll = os.path.join(HOMEPATH, dll)  + '.dll'
        self.copy(dll, outf)
        self.copy(self.pkg.name, outf)
        outf.close()
        os.chmod(self.name, 0755)
        _save_data(self.out,
                   (self.name, self.console, self.debug, self.icon,
                    self.versrsrc, self.manifest, self.resources, self.strip, self.upx, mtime(self.name)))
        return 1


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
                if isinstance(arg, EXE):
                    for tocnm, fnm, typ in arg.toc:
                        if tocnm == os.path.basename(arg.name) + ".manifest":
                            self.toc.append((tocnm, fnm, typ))
                    if not arg.append_pkg:
                        self.toc.append((os.path.basename(arg.pkgname), arg.pkgname, 'PKG'))
                self.toc.extend(arg.dependencies)
            else:
                self.toc.extend(arg)
        self.__postinit__()

    GUTS = (('name',            _check_guts_eq),
            ('strip_binaries',  _check_guts_eq),
            ('upx_binaries',    _check_guts_eq),
            ('toc',             _check_guts_eq), # additional check below
            )

    def check_guts(self, last_build):
        _rmdir(self.name)
        data = Target.get_guts(self, last_build)
        if not data:
            return True
        toc = data[-1]
        for inm, fnm, typ in self.toc:
            if typ == 'EXTENSION':
                ext = os.path.splitext(fnm)[1]
                test = os.path.join(self.name, inm+ext)
            else:
                test = os.path.join(self.name, os.path.basename(fnm))
            if not os.path.exists(test):
                print "building %s because %s is missing" % (self.outnm, test)
                return 1
            if mtime(fnm) > mtime(test):
                print "building %s because %s is more recent" % (self.outnm, fnm)
                return 1
        return 0

    def assemble(self):
        print "building COLLECT", os.path.basename(self.out)
        if not os.path.exists(self.name):
            os.makedirs(self.name)
        toc = addSuffixToExtensions(self.toc)
        for inm, fnm, typ in toc:
            if not os.path.isfile(fnm) and check_egg(fnm):
                # file is contained within python egg, it is added with the egg
                continue
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
        _save_data(self.out,
                 (self.name, self.strip_binaries, self.upx_binaries, self.toc))
        return 1


class BUNDLE(Target):
    def __init__(self, *args, **kws):

        # BUNDLE only has a sense under Mac OS X, it's a noop on other platforms
        if not sys.platform.startswith("darwin"):
            return

        Target.__init__(self)
        self.name = kws.get('name', None)
        if self.name is not None:
            self.appname = os.path.splitext(os.path.basename(self.name))[0]
        self.version = kws.get("version", "0.0.0")
        self.toc = TOC()
        for arg in args:
            if isinstance(arg, EXE):
                self.toc.append((os.path.basename(arg.name), arg.name, arg.typ))
                self.toc.extend(arg.dependencies)
            elif isinstance(arg, TOC):
                self.toc.extend(arg)
            elif isinstance(arg, COLLECT):
                self.toc.extend(arg.toc)
            else:
                print "unsupported entry %s", arg.__class__.__name__
        # Now, find values for app filepath (name), app name (appname), and name
        # of the actual executable (exename) from the first EXECUTABLE item in
        # toc, which might have come from a COLLECT too (not from an EXE).
        for inm, name, typ in self.toc:
            if typ == "EXECUTABLE":
                self.exename = name
                if self.name is None:
                    self.appname = "Mac%s" % (os.path.splitext(inm)[0],)
                    self.name = os.path.join(SPECPATH, self.appname + ".app")
                break
        self.__postinit__()

    GUTS = (('toc',             _check_guts_eq), # additional check below
            )

    def check_guts(self, last_build):
        _rmdir(self.name)
        data = Target.get_guts(self, last_build)
        if not data:
            return True
        toc = data[-1]
        for inm, fnm, typ in self.toc:
            test = os.path.join(self.name, os.path.basename(fnm))
            if not os.path.exists(test):
                print "building %s because %s is missing" % (self.outnm, test)
                return 1
            if mtime(fnm) > mtime(test):
                print "building %s because %s is more recent" % (self.outnm, fnm)
                return 1
        return 0

    def assemble(self):
        print "building BUNDLE", os.path.basename(self.out)

        if os.path.exists(self.name):
            shutil.rmtree(self.name)
        # Create a minimal Mac bundle structure
        os.makedirs(os.path.join(self.name, "Contents", "MacOS"))
        os.makedirs(os.path.join(self.name, "Contents", "Resources"))
        os.makedirs(os.path.join(self.name, "Contents", "Frameworks"))
        # Key/values for a minimal Info.plist file
        info_plist_dict = {"CFBundleDisplayName": self.appname,
                           "CFBundleName": self.appname,
                           "CFBundleExecutable": os.path.basename(self.exename),
                           "CFBundleIconFile": "App.icns",
                           "CFBundleInfoDictionaryVersion": "6.0",
                           "CFBundlePackageType": "APPL",
                           "CFBundleShortVersionString": self.version,

                           # Setting this to 1 will cause Mac OS X *not* to show
                           # a dock icon for the PyInstaller process which
                           # decompresses the real executable's contents. As a
                           # side effect, the main application doesn't get one
                           # as well, but at startup time the loader will take
                           # care of transforming the process type.
                           "LSBackgroundOnly": "1",

                           }
        info_plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>"""
        for k, v in info_plist_dict.items():
            info_plist += "<key>%s</key>\n<string>%s</string>\n" % (k, v)
        info_plist += """</dict>
</plist>"""
        f = open(os.path.join(self.name, "Contents", "Info.plist"), "w")
        f.write(info_plist)
        f.close()

        toc = addSuffixToExtensions(self.toc)
        for inm, fnm, typ in toc:
            tofnm = os.path.join(self.name, "Contents", "MacOS", inm)
            todir = os.path.dirname(tofnm)
            if not os.path.exists(todir):
                os.makedirs(todir)
            shutil.copy2(fnm, tofnm)
        return 1


class TOC(UserList.UserList):
    def __init__(self, initlist=None):
        UserList.UserList.__init__(self)
        self.fltr = {}
        if initlist:
            for tpl in initlist:
                self.append(tpl)
    def append(self, tpl):
        try:
            fn = tpl[0]
            if tpl[2] == "BINARY":
                # Normalize the case for binary files only (to avoid duplicates
                # for different cases under Windows). We can't do that for
                # Python files because the import semantic (even at runtime)
                # depends on the case.
                fn = os.path.normcase(fn)
            if not self.fltr.get(fn):
                self.data.append(tpl)
                self.fltr[fn] = 1
        except TypeError:
            print "TOC found a %s, not a tuple" % tpl
            raise
    def insert(self, pos, tpl):
        fn = tpl[0]
        if tpl[2] == "BINARY":
            fn = os.path.normcase(fn)
        if not self.fltr.get(fn):
            self.data.insert(pos, tpl)
            self.fltr[fn] = 1
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

    GUTS = (('root',     _check_guts_eq),
            ('prefix',   _check_guts_eq),
            ('excludes', _check_guts_eq),
            ('toc',      None),
            )

    def check_guts(self, last_build):
        data = Target.get_guts(self, last_build)
        if not data:
            return True
        stack = [ data[0] ] # root
        toc = data[3] # toc
        while stack:
            d = stack.pop()
            if mtime(d) > last_build:
                print "building %s because directory %s changed" % (self.outnm, d)
                return True
            for nm in os.listdir(d):
                path = os.path.join(d, nm)
                if os.path.isdir(path):
                    stack.append(path)
        self.data = toc
        return False

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
        self.data = rslt
        try:
            oldstuff = _load_data(self.out)
        except:
            oldstuff = None
        newstuff = (self.root, self.prefix, self.excludes, self.data)
        if oldstuff != newstuff:
            _save_data(self.out, newstuff)
            return 1
        print self.out, "no change!"
        return 0

def TkTree():
    tclroot = config['TCL_root']
    tclnm = os.path.join('_MEI', config['TCL_dirname'])
    tkroot = config['TK_root']
    tknm = os.path.join('_MEI', config['TK_dirname'])
    tcltree = Tree(tclroot, tclnm, excludes=['demos','encoding','*.lib'])
    tktree = Tree(tkroot, tknm, excludes=['demos','encoding','*.lib'])
    return tcltree + tktree

def TkPKG():
    return PKG(TkTree(), name='tk.pkg')

#---

def build(spec):
    global SPECPATH, BUILDPATH, WARNFILE, rthooks, SPEC, specnm
    rthooks = _load_data(os.path.join(HOMEPATH, 'rthooks.dat'))
    SPEC = spec
    SPECPATH, specnm = os.path.split(spec)
    specnm = os.path.splitext(specnm)[0]
    if SPECPATH == '':
        SPECPATH = os.getcwd()
    WARNFILE = os.path.join(SPECPATH, 'warn%s.txt' % specnm)
    BUILDPATH = os.path.join(SPECPATH, 'build',
                             "pyi." + config['target_platform'], specnm)
    if opts.buildpath != parser.get_option('--buildpath').default:
        bpath = opts.buildpath
        if os.path.isabs(bpath):
            BUILDPATH = bpath
        else:
            BUILDPATH = os.path.join(SPECPATH, bpath)
    if not os.path.exists(BUILDPATH):
        os.makedirs(BUILDPATH)
    execfile(spec)


def main(specfile, configfilename):
    global target_platform, target_iswin, config
    global icon, versionInfo, winresource, winmanifest, pyasm

    try:
        config = _load_data(configfilename)
    except IOError:
        print "You must run Configure.py before building!"
        sys.exit(1)

    target_platform = config.get('target_platform', sys.platform)
    target_iswin = target_platform[:3] == 'win'

    if target_platform == sys.platform:
        # _not_ cross compiling
        if config['pythonVersion'] != sys.version:
            print "The current version of Python is not the same with which PyInstaller was configured."
            print "Please re-run Configure.py with this version."
            sys.exit(1)

    if config.setdefault('pythonDebug', None) != __debug__:
        print "python optimization flags changed: rerun Configure.py with the same [-O] option"
        print "Configure.py optimize=%s, Build.py optimize=%s" % (not config['pythonDebug'], not __debug__)
        sys.exit(1)

    if iswin:
        import winmanifest

    if config['hasRsrcUpdate']:
        import icon, versionInfo, winresource
        pyasm = bindepend.getAssemblies(config['python'])
    else:
        pyasm = None

    if config['hasUPX']:
        setupUPXFlags()

    if not config['useELFEXE']:
        EXE.append_pkg = 0

    build(specfile)


from pyi_optparse import OptionParser
parser = OptionParser('%prog [options] specfile')
parser.add_option('-C', '--configfile',
                  default=os.path.join(HOMEPATH, 'config.dat'),
                  help='Name of generated configfile (default: %default)')
parser.add_option('-o', '--buildpath',
                  default=os.path.join('SPECPATH', 'build',
                                       'pyi.TARGET_PLATFORM', 'SPECNAME'),
                  help='Buildpath (default: %default)')
parser.add_option('-y', '--noconfirm',
                  action="store_true", default=False,
                  help='Remove output directory (default: %s) without '
                       'confirmation' % os.path.join('SPECPATH', 'dist'))

if __name__ == '__main__':
    opts, args = parser.parse_args()
    if len(args) != 1:
        parser.error('Requires exactly one .spec-file')

    main(args[0], configfilename=opts.configfile)
else:
    opts = parser.get_default_values()
