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
import py_compile
import imp
import tempfile
import UserList
import bindepend

from PyInstaller.loader import archive, carchive

import PyInstaller.depend.imptracker
import PyInstaller.depend.modules

from PyInstaller import HOMEPATH, CONFIGDIR, PLATFORM
from PyInstaller import is_win, is_unix, is_aix, is_darwin, is_cygwin
from PyInstaller import is_py23, is_py24
import PyInstaller.compat as compat

from PyInstaller.compat import hashlib, set
from PyInstaller.depend import dylib
from PyInstaller.utils import misc


import PyInstaller.log as logging
if is_win:
    from PyInstaller.utils import winmanifest


logger = logging.getLogger('PyInstaller.build')

STRINGTYPE = type('')
TUPLETYPE = type((None,))
UNCOMPRESSED, COMPRESSED = range(2)

DEFAULT_BUILDPATH = os.path.join('SPECPATH', 'build',
                                 'pyi.TARGET_PLATFORM', 'SPECNAME')

SPEC = None
SPECPATH = None
BUILDPATH = None
WARNFILE = None
NOCONFIRM = None

# Some modules are included if they are detected at build-time or
# if a command-line argument is specified. (e.g. --ascii)
HIDDENIMPORTS = []

rthooks = {}


def _save_data(filename, data):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    outf = open(filename, 'w')
    pprint.pprint(data, outf)
    outf.close()


def _load_data(filename):
    return eval(open(filename, 'rU').read())


def setupUPXFlags():
    f = compat.getenv("UPX", "")
    if is_win and is_py24:
        # Binaries built with Visual Studio 7.1 require --strip-loadconf
        # or they won't compress. Configure.py makes sure that UPX is new
        # enough to support --strip-loadconf.
        f = "--strip-loadconf " + f
    # Do not compress any icon, so that additional icons in the executable
    # can still be externally bound
    f = "--compress-icons=0 " + f
    f = "--best " + f
    compat.setenv("UPX", f)


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
    basepath = os.path.join(BUILDPATH, "localpycos")

    new_toc = []
    for (nm, fnm, typ) in toc:
        if typ != 'PYMODULE':
            new_toc.append((nm, fnm, typ))
            continue

        # Trim the terminal "c" or "o"
        source_fnm = fnm[:-1]

        # We need to perform a build ourselves if the source is newer
        # than the compiled, or the compiled doesn't exist, or if it
        # has been written by a different Python version.
        needs_compile = (mtime(source_fnm) > mtime(fnm)
                         or
                         open(fnm, 'rb').read()[:4] != imp.get_magic())
        if needs_compile:
            try:
                py_compile.compile(source_fnm, fnm)
                logger.debug("compiled %s", source_fnm)
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

                leading = os.path.join(basepath, *leading)

                if not os.path.exists(leading):
                    os.makedirs(leading)

                fnm = os.path.join(leading, mod_name + ext)
                needs_compile = (mtime(source_fnm) > mtime(fnm)
                                 or
                                 open(fnm, 'rb').read()[:4] != imp.get_magic())
                if needs_compile:
                    py_compile.compile(source_fnm, fnm)
                    logger.debug("compiled %s", source_fnm)

        new_toc.append((nm, fnm, typ))

    return new_toc


def addSuffixToExtensions(toc):
    """
    Returns a new TOC with proper library suffix for EXTENSION items.
    """
    new_toc = TOC()
    for inm, fnm, typ in toc:
        if typ in ('EXTENSION', 'DEPENDENCY'):
            binext = os.path.splitext(fnm)[1]
            if not os.path.splitext(inm)[1] == binext:
                inm = inm + binext
        new_toc.append((inm, fnm, typ))
    return new_toc


#--- functons for checking guts ---

def _check_guts_eq(attr, old, new, last_build):
    """
    rebuild is required if values differ
    """
    if old != new:
        logger.info("building because %s changed", attr)
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
            logger.info("building because %s changed", fnm)
            return True
        elif pyc and mtime(fnm[:-1]) > last_build:
            logger.info("building because %s changed", fnm[:-1])
            return True
    return False


def _check_guts_toc(attr, old, toc, last_build, pyc=0):
    """
    rebuild is required if either toc content changed if mtimes of
    files listed in old toc are newer than ast_build

    if pyc=1, check for .py files, too
    """
    return (_check_guts_eq(attr, old, toc, last_build)
            or _check_guts_toc_mtime(attr, old, toc, last_build, pyc=pyc))


def _check_path_overlap(path):
    """
    Check that path does not overlap with BUILDPATH or SPECPATH (i.e.
    BUILDPATH and SPECPATH may not start with path, which could be
    caused by a faulty hand-edited specfile)

    Raise SystemExit if there is overlap, return True otherwise
    """
    specerr = 0
    if BUILDPATH.startswith(path):
        logger.error('Specfile error: The output path "%s" contains '
                     'BUILDPATH (%s)', path, BUILDPATH)
        specerr += 1
    if SPECPATH.startswith(path):
        logger.error('Specfile error: The output path "%s" contains '
                     'SPECPATH (%s)', path, SPECPATH)
        specerr += 1
    if specerr:
        raise SystemExit('Error: Please edit/recreate the specfile (%s) '
                         'and set a different output name (e.g. "dist").'
                         % SPEC)
    return True


def _rmtree(path):
    """
    Remove directory and all its contents, but only after user confirmation,
    or if the -y option is set
    """
    if NOCONFIRM:
        choice = 'y'
    elif sys.stdout.isatty():
        choice = raw_input('WARNING: The output directory "%s" and ALL ITS '
                           'CONTENTS will be REMOVED! Continue? (y/n)' % path)
    else:
        raise SystemExit('Error: The output directory "%s" is not empty. '
                         'Please remove all its contents or use the '
                         '-y option (remove output directory without '
                         'confirmation).' % path)
    if choice.strip().lower() == 'y':
        logger.info('Removing dir %s', path)
        shutil.rmtree(path)
    else:
        raise SystemExit('User aborted')


def check_egg(pth):
    """Check if path points to a file inside a python egg file (or to an egg
       directly)."""
    if is_py23:
        if os.path.altsep:
            pth = pth.replace(os.path.altsep, os.path.sep)
        components = pth.split(os.path.sep)
        sep = os.path.sep
    else:
        components = pth.replace("\\", "/").split("/")
        sep = "/"
        if is_win:
            sep = "\\"
    for i, name in zip(range(0, len(components)), components):
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
        # Get a (per class) unique number to avoid conflicts between
        # toc objects
        self.invcnum = self.__class__.invcnum
        self.__class__.invcnum += 1
        self.out = os.path.join(BUILDPATH, 'out%02d-%s.toc' %
                                (self.invcnum, self.__class__.__name__))
        self.outnm = os.path.basename(self.out)
        self.dependencies = TOC()

    def __postinit__(self):
        logger.info("checking %s", self.__class__.__name__)
        if self.check_guts(mtime(self.out)):
            self.assemble()

    GUTS = []

    def check_guts(self, last_build):
        pass

    def get_guts(self, last_build, missing='missing or bad'):
        """
        returns None if guts have changed
        """
        try:
            data = _load_data(self.out)
        except:
            logger.info("building because %s %s", os.path.basename(self.out), missing)
            return None

        if len(data) != len(self.GUTS):
            logger.info("building because %s is bad", self.outnm)
            return None
        for i, (attr, func) in enumerate(self.GUTS):
            if func is None:
                # no check for this value
                continue
            if func(attr, data[i], getattr(self, attr), last_build):
                return None
        return data


class Analysis(Target):
    _old_scripts = set((
        absnormpath(os.path.join(HOMEPATH, "support", "_mountzlib.py")),
        absnormpath(os.path.join(CONFIGDIR, "support", "useUnicode.py")),
        absnormpath(os.path.join(CONFIGDIR, "support", "useTK.py")),
        absnormpath(os.path.join(HOMEPATH, "support", "useUnicode.py")),
        absnormpath(os.path.join(HOMEPATH, "support", "useTK.py")),
        absnormpath(os.path.join(HOMEPATH, "support", "unpackTK.py")),
        absnormpath(os.path.join(HOMEPATH, "support", "removeTK.py")),
        ))

    def __init__(self, scripts=None, pathex=None, hiddenimports=None,
                 hookspath=None, excludes=None):
        Target.__init__(self)
        # Include initialization Python code in PyInstaller analysis.
        _init_code_path = os.path.join(HOMEPATH, 'PyInstaller', 'loader')
        self.inputs = [
            os.path.join(HOMEPATH, "support", "_pyi_bootstrap.py"),
            os.path.join(_init_code_path, 'archive.py'),
            os.path.join(_init_code_path, 'carchive.py'),
            os.path.join(_init_code_path, 'iu.py'),
            ]
        for script in scripts:
            if absnormpath(script) in self._old_scripts:
                logger.warn('Ignoring obsolete auto-added script %s', script)
                continue
            if not os.path.exists(script):
                raise ValueError("script '%s' not found" % script)
            self.inputs.append(script)
        self.pathex = []
        if pathex:
            self.pathex = [absnormpath(path) for path in pathex]

        self.hiddenimports = hiddenimports or []
        # Include modules detected at build time. Like 'codecs' and encodings.
        self.hiddenimports.extend(HIDDENIMPORTS)

        self.hookspath = hookspath
        self.excludes = excludes
        self.scripts = TOC()
        self.pure = TOC()
        self.binaries = TOC()
        self.zipfiles = TOC()
        self.datas = TOC()
        self.dependencies = TOC()
        self.__postinit__()

    GUTS = (('inputs', _check_guts_eq),
            ('pathex', _check_guts_eq),
            ('hookspath', _check_guts_eq),
            ('excludes', _check_guts_eq),
            ('scripts', _check_guts_toc_mtime),
            ('pure', lambda *args: apply(_check_guts_toc_mtime,
                                              args, {'pyc': 1})),
            ('binaries', _check_guts_toc_mtime),
            ('zipfiles', _check_guts_toc_mtime),
            ('datas', _check_guts_toc_mtime),
            ('hiddenimports', _check_guts_eq),
            )

    def check_guts(self, last_build):
        if last_build == 0:
            logger.info("building %s because %s non existent", self.__class__.__name__, self.outnm)
            return True
        for fnm in self.inputs:
            if mtime(fnm) > last_build:
                logger.info("building because %s changed", fnm)
                return True

        data = Target.get_guts(self, last_build)
        if not data:
            return True
        scripts, pure, binaries, zipfiles, datas, hiddenimports = data[-6:]
        self.scripts = TOC(scripts)
        self.pure = TOC(pure)
        self.binaries = TOC(binaries)
        self.zipfiles = TOC(zipfiles)
        self.datas = TOC(datas)
        self.hiddenimports = hiddenimports
        return False

    def assemble(self):
        logger.info("running Analysis %s", os.path.basename(self.out))
        # Reset seen variable to correctly discover dependencies
        # if there are multiple Analysis in a single specfile.
        bindepend.seen = {}

        python = sys.executable
        if not is_win:
            while os.path.islink(python):
                python = os.path.join(os.path.dirname(python), os.readlink(python))
            depmanifest = None
        else:
            depmanifest = winmanifest.Manifest(type_="win32", name=specnm,
                                               processorArchitecture=winmanifest.processor_architecture(),
                                               version=(1, 0, 0, 0))
            depmanifest.filename = os.path.join(BUILDPATH,
                                                specnm + ".exe.manifest")

        binaries = []  # binaries to bundle

        # Always add Python's dependencies first
        # This ensures that its assembly depencies under Windows get pulled in
        # first, so that .pyd files analyzed later which may not have their own
        # manifest and may depend on DLLs which are part of an assembly
        # referenced by Python's manifest, don't cause 'lib not found' messages
        binaries.extend(bindepend.Dependencies([('', python, '')],
                                               manifest=depmanifest)[1:])

        ###################################################
        # Scan inputs and prepare:
        dirs = {}  # input directories
        pynms = []  # python filenames with no extension
        for script in self.inputs:
            if not os.path.exists(script):
                raise SystemExit("Error: Analysis: script %s not found!" % script)
            d, base = os.path.split(script)
            if not d:
                d = os.getcwd()
            d = absnormpath(d)
            pynm, ext = os.path.splitext(base)
            dirs[d] = 1
            pynms.append(pynm)
        ###################################################
        # Initialize importTracker and analyze scripts
        importTracker = PyInstaller.depend.imptracker.ImportTracker(
                dirs.keys() + self.pathex, self.hookspath, self.excludes)
        PyInstaller.__pathex__ = self.pathex[:]
        scripts = []  # will contain scripts to bundle
        for i, script in enumerate(self.inputs):
            logger.info("Analyzing %s", script)
            importTracker.analyze_script(script)
            scripts.append((pynms[i], script, 'PYSOURCE'))
        PyInstaller.__pathex__ = []

        # analyze the script's hidden imports
        for modnm in self.hiddenimports:
            if modnm in importTracker.modules:
                logger.info("Hidden import %r has been found otherwise", modnm)
                continue
            logger.info("Analyzing hidden import %r", modnm)
            importTracker.analyze_one(modnm)
            if not modnm in importTracker.modules:
                logger.error("Hidden import %r not found", modnm)

        ###################################################
        # Fills pure, binaries and rthookcs lists to TOC
        pure = []     # pure python modules
        zipfiles = []  # zipfiles to bundle
        datas = []    # datafiles to bundle
        rthooks = []  # rthooks if needed

        # Find rthooks.
        logger.info("Looking for run-time hooks")
        for modnm, mod in importTracker.modules.items():
            rthooks.extend(_findRTHook(modnm))

        # Analyze rthooks. Runtime hooks has to be also analyzed.
        # Otherwise some dependencies could be missing.
        # Data structure in format:
        # ('rt_hook_mod_name', '/rt/hook/file/name.py', 'PYSOURCE')
        for hook_mod, hook_file, mod_type in rthooks:
            logger.info("Analyzing rthook %s", hook_file)
            importTracker.analyze_script(hook_file)

        for modnm, mod in importTracker.modules.items():
            # FIXME: why can we have a mod == None here?
            if mod is None:
                continue

            datas.extend(mod.datas)

            if isinstance(mod, PyInstaller.depend.modules.BuiltinModule):
                pass
            elif isinstance(mod, PyInstaller.depend.modules.ExtensionModule):
                binaries.append((mod.__name__, mod.__file__, 'EXTENSION'))
                # allows hooks to specify additional dependency
                # on other shared libraries loaded at runtime (by dlopen)
                binaries.extend(mod.binaries)
            elif isinstance(mod, (PyInstaller.depend.modules.PkgInZipModule, PyInstaller.depend.modules.PyInZipModule)):
                zipfiles.append(("eggs/" + os.path.basename(str(mod.owner)),
                                 str(mod.owner), 'ZIPFILE'))
            else:
                # mf.PyModule instances expose a list of binary
                # dependencies, most probably shared libraries accessed
                # via ctypes. Add them to the overall required binaries.
                binaries.extend(mod.binaries)
                if modnm != '__main__':
                    pure.append((modnm, mod.__file__, 'PYMODULE'))

        # Add remaining binary dependencies
        binaries.extend(bindepend.Dependencies(binaries,
                                               manifest=depmanifest))
        if is_win:
            depmanifest.writeprettyxml()
        self.fixMissingPythonLib(binaries)
        if zipfiles:
            scripts.insert(-1, ("_pyi_egg_install.py", os.path.join(HOMEPATH, "support/_pyi_egg_install.py"), 'PYSOURCE'))
        # Add realtime hooks just before the last script (which is
        # the entrypoint of the application).
        scripts[-1:-1] = rthooks
        self.scripts = TOC(scripts)
        self.pure = TOC(pure)
        self.binaries = TOC(binaries)
        self.zipfiles = TOC(zipfiles)
        self.datas = TOC(datas)
        try:  # read .toc
            oldstuff = _load_data(self.out)
        except:
            oldstuff = None

        self.pure = TOC(compile_pycos(self.pure))

        newstuff = tuple([getattr(self, g[0]) for g in self.GUTS])
        if oldstuff != newstuff:
            _save_data(self.out, newstuff)
            wf = open(WARNFILE, 'w')
            for ln in importTracker.getwarnings():
                wf.write(ln + '\n')
            wf.close()
            logger.info("Warnings written to %s", WARNFILE)
            return 1
        logger.info("%s no change!", self.out)
        return 0

    def fixMissingPythonLib(self, binaries):
        """Add the Python library if missing from the binaries.

        Some linux distributions (e.g. debian-based) statically build the
        Python executable to the libpython, so bindepend doesn't include
        it in its output.

        Darwin custom builds could possibly also have non-framework style libraries,
        so this method also checks for that variant as well.
        """

        if is_aix:
            # Shared libs on AIX are archives with shared object members, thus the ".a" suffix.
            names = ('libpython%d.%d.a' % sys.version_info[:2],)
        elif is_unix:
            # Other *nix platforms.
            names = ('libpython%d.%d.so' % sys.version_info[:2],)
        elif is_darwin:
            names = ('Python', 'libpython%d.%d.dylib' % sys.version_info[:2])
        else:
            return

        for (nm, fnm, typ) in binaries:
            for name in names:
                if typ == 'BINARY' and name in fnm:
                    # lib found
                    return

        # Resume search using the first item in names.
        name = names[0]

        logger.info('Looking for Python library %s', name)

        if is_unix:
            lib = bindepend.findLibrary(name)
            if lib is None:
                raise IOError("Python library not found!")

        elif is_darwin:
            # On MacPython, Analysis.assemble is able to find the libpython with
            # no additional help, asking for sys.executable dependencies.
            # However, this fails on system python, because the shared library
            # is not listed as a dependency of the binary (most probably it's
            # opened at runtime using some dlopen trickery).
            # This happens on Mac OS X when Python is compiled as Framework.

            # Python compiled as Framework contains same values in sys.prefix
            # and exec_prefix. That's why we can use just sys.prefix.
            # In virtualenv PyInstaller is not able to find Python library.
            # We need special care for this case.
            if compat.is_virtualenv:
                py_prefix = sys.real_prefix
            else:
                py_prefix = sys.prefix

            logger.info('Looking for Python library in %s', py_prefix)

            lib = os.path.join(py_prefix, name)
            if not os.path.exists(lib):
                raise IOError("Python library not found!")

        binaries.append((os.path.basename(lib), lib, 'BINARY'))


def _findRTHook(modnm):
    rslt = []
    for script in rthooks.get(modnm) or []:
        nm = os.path.basename(script)
        nm = os.path.splitext(nm)[0]
        if os.path.isabs(script):
            path = script
        else:
            path = os.path.join(HOMEPATH, script)
        rslt.append((nm, path, 'PYSOURCE'))
    return rslt


class PYZ(Target):
    typ = 'PYZ'

    def __init__(self, toc, name=None, level=9, crypt=None):
        Target.__init__(self)
        self.toc = toc
        self.name = name
        if name is None:
            self.name = self.out[:-3] + 'pyz'
        # Level of zlib compression.
        self.level = level
        if config['useCrypt'] and crypt is not None:
            self.crypt = archive.Keyfile(crypt).key
        else:
            self.crypt = None
        self.dependencies = compile_pycos(config['PYZ_dependencies'])
        self.__postinit__()

    GUTS = (('name', _check_guts_eq),
            ('level', _check_guts_eq),
            ('crypt', _check_guts_eq),
            ('toc', _check_guts_toc),  # todo: pyc=1
            )

    def check_guts(self, last_build):
        if not os.path.exists(self.name):
            logger.info("rebuilding %s because %s is missing",
                        self.outnm, os.path.basename(self.name))
            return True

        data = Target.get_guts(self, last_build)
        if not data:
            return True
        return False

    def assemble(self):
        logger.info("building PYZ %s", os.path.basename(self.out))
        pyz = archive.ZlibArchive(level=self.level, crypt=self.crypt)
        toc = self.toc - config['PYZ_dependencies']
        pyz.build(self.name, toc)
        _save_data(self.out, (self.name, self.level, self.crypt, self.toc))
        return 1


def cacheDigest(fnm):
    data = open(fnm, "rb").read()
    digest = hashlib.md5(data).digest()
    return digest


def checkCache(fnm, strip=0, upx=0, dist_nm=None):
    """
    Cache prevents preprocessing binary files again and again.

    'dist_nm'  Filename relative to dist directory. We need it on Mac
               to determine level of paths for @loader_path like
               '@loader_path/../../' for qt4 plugins.
    """
    # On darwin a cache is required anyway to keep the libaries
    # with relative install names. Caching on darwin does not work
    # since we need to modify binary headers to use relative paths
    # to dll depencies and starting with '@loader_path'.

    if ((not strip and not upx and not is_darwin and not is_win)
        or fnm.lower().endswith(".manifest")):
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
    # Make cachedir per Python major/minor version.
    # This allows parallel building of executables with different
    # Python versions as one user.
    pyver = ('py%d%s') % (sys.version_info[0], sys.version_info[1])
    cachedir = os.path.join(CONFIGDIR, 'bincache%d%d_%s' % (strip, upx, pyver))
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
    if basenm in cache_index:
        if digest != cache_index[basenm]:
            os.remove(cachedfile)
        else:
            # On Mac OS X we need relative paths to dll dependencies
            # starting with @executable_path
            if is_darwin:
                dylib.mac_set_relative_dylib_deps(cachedfile, dist_nm)
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
        cmd = [upx_executable, bestopt, "-q", cachedfile]
    else:
        if strip:
            # -S = strip only debug symbols.
            # The default strip behaviour breaks some shared libraries
            # under Mac OSX
            cmd = ["strip", "-S", cachedfile]
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
                logger.error(os.path.abspath(cachedfile))
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
                            logger.error("Cannot parse manifest resource %s, "
                                         "%s from", name, language)
                            logger.error(cachedfile)
                            logger.exception(exc)
                        else:
                            # Fix the embedded manifest (if any):
                            # Extension modules built with Python 2.6.5 have
                            # an empty <dependency> element, we need to add
                            # dependentAssemblies from python.exe for
                            # pyinstaller
                            olen = len(manifest.dependentAssemblies)
                            _depNames = set([dep.name for dep in
                                             manifest.dependentAssemblies])
                            for pydep in pyasm:
                                if not pydep.name in _depNames:
                                    logger.info("Adding %r to dependent "
                                                "assemblies of %r",
                                                pydep.name, cachedfile)
                                    manifest.dependentAssemblies.append(pydep)
                                    _depNames.update(pydep.name)
                            if len(manifest.dependentAssemblies) > olen:
                                try:
                                    manifest.update_resources(os.path.abspath(cachedfile),
                                                              [name],
                                                              [language])
                                except Exception, e:
                                    logger.error(os.path.abspath(cachedfile))
                                    raise

    if cmd:
        try:
            compat.exec_command(*cmd)
        except OSError, e:
            raise SystemExit("Execution failed: %s" % e)

    # update cache index
    cache_index[basenm] = digest
    _save_data(cacheindexfn, cache_index)

    # On Mac OS X we need relative paths to dll dependencies
    # starting with @executable_path
    if is_darwin:
        dylib.mac_set_relative_dylib_deps(cachedfile, dist_nm)
    return cachedfile


UNCOMPRESSED, COMPRESSED, ENCRYPTED = range(3)


class PKG(Target):
    typ = 'PKG'
    xformdict = {'PYMODULE': 'm',
                 'PYSOURCE': 's',
                 'EXTENSION': 'b',
                 'PYZ': 'z',
                 'PKG': 'a',
                 'DATA': 'x',
                 'BINARY': 'b',
                 'ZIPFILE': 'Z',
                 'EXECUTABLE': 'b',
                 'DEPENDENCY': 'd'}

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
            self.cdict = {'EXTENSION': COMPRESSED,
                          'DATA': COMPRESSED,
                          'BINARY': COMPRESSED,
                          'EXECUTABLE': COMPRESSED,
                          'PYSOURCE': COMPRESSED,
                          'PYMODULE': COMPRESSED}
            if self.crypt:
                self.cdict['PYSOURCE'] = ENCRYPTED
                self.cdict['PYMODULE'] = ENCRYPTED
        self.__postinit__()

    GUTS = (('name', _check_guts_eq),
            ('cdict', _check_guts_eq),
            ('toc', _check_guts_toc_mtime),
            ('exclude_binaries', _check_guts_eq),
            ('strip_binaries', _check_guts_eq),
            ('upx_binaries', _check_guts_eq),
            ('crypt', _check_guts_eq),
            )

    def check_guts(self, last_build):
        if not os.path.exists(self.name):
            logger.info("rebuilding %s because %s is missing",
                        self.outnm, os.path.basename(self.name))
            return 1

        data = Target.get_guts(self, last_build)
        if not data:
            return True
        # todo: toc equal
        return False

    def assemble(self):
        logger.info("building PKG %s", os.path.basename(self.name))
        trash = []
        mytoc = []
        seen = {}
        toc = addSuffixToExtensions(self.toc)
        for inm, fnm, typ in toc:
            if not os.path.isfile(fnm) and check_egg(fnm):
                # file is contained within python egg, it is added with the egg
                continue
            if typ in ('BINARY', 'EXTENSION', 'DEPENDENCY'):
                if self.exclude_binaries and typ != 'DEPENDENCY':
                    self.dependencies.append((inm, fnm, typ))
                else:
                    fnm = checkCache(fnm, self.strip_binaries,
                                     self.upx_binaries and (is_win or is_cygwin)
                                     and config['hasUPX'], dist_nm=inm)
                    # Avoid importing the same binary extension twice. This might
                    # happen if they come from different sources (eg. once from
                    # binary dependence, and once from direct import).
                    if typ == 'BINARY' and fnm in seen:
                        continue
                    seen[fnm] = 1
                    mytoc.append((inm, fnm, self.cdict.get(typ, 0),
                                  self.xformdict.get(typ, 'b')))
            elif typ == 'OPTION':
                mytoc.append((inm, '', 0, 'o'))
            else:
                mytoc.append((inm, fnm, self.cdict.get(typ, 0), self.xformdict.get(typ, 'b')))
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
        self.console = kws.get('console', 1)
        self.debug = kws.get('debug', 0)
        self.name = kws.get('name', None)
        self.icon = kws.get('icon', None)
        self.versrsrc = kws.get('version', None)
        self.manifest = kws.get('manifest', None)
        self.resources = kws.get('resources', [])
        self.strip = kws.get('strip', None)
        self.upx = kws.get('upx', None)
        self.crypt = kws.get('crypt', 0)
        self.exclude_binaries = kws.get('exclude_binaries', 0)
        self.append_pkg = kws.get('append_pkg', self.append_pkg)
        if self.name is None:
            self.name = self.out[:-3] + 'exe'
        if not os.path.isabs(self.name):
            self.name = os.path.join(SPECPATH, self.name)
        if is_win or is_cygwin:
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
        if is_win:
            filename = os.path.join(BUILDPATH, specnm + ".exe.manifest")
            self.manifest = winmanifest.create_manifest(filename, self.manifest,
                self.console)
            self.toc.append((os.path.basename(self.name) + ".manifest", filename,
                'BINARY'))
        self.pkg = PKG(self.toc, cdict=kws.get('cdict', None),
                       exclude_binaries=self.exclude_binaries,
                       strip_binaries=self.strip, upx_binaries=self.upx,
                       crypt=self.crypt)
        self.dependencies = self.pkg.dependencies
        self.__postinit__()

    GUTS = (('name', _check_guts_eq),
            ('console', _check_guts_eq),
            ('debug', _check_guts_eq),
            ('icon', _check_guts_eq),
            ('versrsrc', _check_guts_eq),
            ('resources', _check_guts_eq),
            ('strip', _check_guts_eq),
            ('upx', _check_guts_eq),
            ('crypt', _check_guts_eq),
            ('mtm', None,),  # checked bellow
            )

    def check_guts(self, last_build):
        if not os.path.exists(self.name):
            logger.info("rebuilding %s because %s missing",
                        self.outnm, os.path.basename(self.name))
            return 1
        if not self.append_pkg and not os.path.exists(self.pkgname):
            logger.info("rebuilding because %s missing",
                        os.path.basename(self.pkgname))
            return 1

        data = Target.get_guts(self, last_build)
        if not data:
            return True

        icon, versrsrc, resources = data[3:6]
        if (icon or versrsrc or resources) and not config['hasRsrcUpdate']:
            # todo: really ignore :-)
            logger.info("ignoring icon, version, manifest and resources = platform not capable")

        mtm = data[-1]
        crypt = data[-2]
        if crypt != self.crypt:
            logger.info("rebuilding %s because crypt option changed", self.outnm)
            return 1
        if mtm != mtime(self.name):
            logger.info("rebuilding %s because mtimes don't match", self.outnm)
            return True
        if mtm < mtime(self.pkg.out):
            logger.info("rebuilding %s because pkg is more recent", self.outnm)
            return True

        return False

    def _bootloader_file(self, exe):
        if not self.console:
            exe = exe + 'w'
        if self.debug:
            exe = exe + '_d'
        return os.path.join("support", "loader", PLATFORM, exe)

    def assemble(self):
        logger.info("building EXE from %s", os.path.basename(self.out))
        trash = []
        if not os.path.exists(os.path.dirname(self.name)):
            os.makedirs(os.path.dirname(self.name))
        outf = open(self.name, 'wb')
        exe = self._bootloader_file('run')
        exe = os.path.join(HOMEPATH, exe)
        if is_win or is_cygwin:
            exe = exe + '.exe'
        if config['hasRsrcUpdate'] and (self.icon or self.versrsrc or
                                        self.resources):
            tmpnm = tempfile.mktemp()
            shutil.copy2(exe, tmpnm)
            os.chmod(tmpnm, 0755)
            if self.icon:
                icon.CopyIcons(tmpnm, self.icon)
            if self.versrsrc:
                versioninfo.SetVersion(tmpnm, self.versrsrc)
            for res in self.resources:
                res = res.split(",")
                for i in range(1, len(res)):
                    try:
                        res[i] = int(res[i])
                    except ValueError:
                        pass
                resfile = res[0]
                restype = resname = reslang = None
                if len(res) > 1:
                    restype = res[1]
                if len(res) > 2:
                    resname = res[2]
                if len(res) > 3:
                    reslang = res[3]
                try:
                    winresource.UpdateResourcesFromResFile(tmpnm, resfile,
                                                        [restype or "*"],
                                                        [resname or "*"],
                                                        [reslang or "*"])
                except winresource.pywintypes.error, exc:
                    if exc.args[0] != winresource.ERROR_BAD_EXE_FORMAT:
                        logger.exception(exc)
                        continue
                    if not restype or not resname:
                        logger.error("resource type and/or name not specified")
                        continue
                    if "*" in (restype, resname):
                        logger.error("no wildcards allowed for resource type "
                                     "and name when source file does not "
                                     "contain resources")
                        continue
                    try:
                        winresource.UpdateResourcesFromDataFile(tmpnm,
                                                             resfile,
                                                             restype,
                                                             [resname],
                                                             [reslang or 0])
                    except winresource.pywintypes.error, exc:
                        logger.exception(exc)
            trash.append(tmpnm)
            exe = tmpnm
        exe = checkCache(exe, self.strip, self.upx and config['hasUPX'])
        self.copy(exe, outf)
        if self.append_pkg:
            logger.info("Appending archive to EXE %s", self.name)
            self.copy(self.pkg.name, outf)
        else:
            logger.info("Copying archive to %s", self.pkgname)
            shutil.copy2(self.pkg.name, self.pkgname)
        outf.close()
        os.chmod(self.name, 0755)
        guts = (self.name, self.console, self.debug, self.icon,
                self.versrsrc, self.resources, self.strip, self.upx,
                self.crypt, mtime(self.name))
        assert len(guts) == len(self.GUTS)
        _save_data(self.out, guts)
        for item in trash:
            os.remove(item)
        return 1

    def copy(self, fnm, outf):
        inf = open(fnm, 'rb')
        while 1:
            data = inf.read(64 * 1024)
            if not data:
                break
            outf.write(data)


class DLL(EXE):
    def assemble(self):
        logger.info("building DLL %s", os.path.basename(self.out))
        outf = open(self.name, 'wb')
        dll = self._bootloader_file('inprocsrvr')
        dll = os.path.join(HOMEPATH, dll) + '.dll'
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
        self.name = kws.get('name', None)
        if self.name is None:
            self.name = 'dist_' + self.out[:-4]
        self.strip_binaries = kws.get('strip', 0)
        self.upx_binaries = kws.get('upx', 0)
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

    GUTS = (('name', _check_guts_eq),
            ('strip_binaries', _check_guts_eq),
            ('upx_binaries', _check_guts_eq),
            ('toc', _check_guts_eq),  # additional check below
            )

    def check_guts(self, last_build):
        # COLLECT always needs to be executed, since it will clean the output
        # directory anyway to make sure there is no existing cruft accumulating
        return 1

    def assemble(self):
        if _check_path_overlap(self.name) and os.path.isdir(self.name):
            _rmtree(self.name)
        logger.info("building COLLECT %s", os.path.basename(self.out))
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
                                 self.upx_binaries and (is_win or is_cygwin)
                                 and config['hasUPX'], dist_nm=inm)
            if typ != 'DEPENDENCY':
                shutil.copy2(fnm, tofnm)
            if typ in ('EXTENSION', 'BINARY'):
                os.chmod(tofnm, 0755)
        _save_data(self.out,
                 (self.name, self.strip_binaries, self.upx_binaries, self.toc))
        return 1


class BUNDLE(Target):
    def __init__(self, *args, **kws):

        # BUNDLE only has a sense under Mac OS X, it's a noop on other platforms
        if not is_darwin:
            return

        # icns icon for app bundle.
        self.icon = kws.get('icon', os.path.join(os.path.dirname(__file__),
            '..', 'source', 'images', 'icon-windowed.icns'))

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
                logger.info("unsupported entry %s", arg.__class__.__name__)
        # Now, find values for app filepath (name), app name (appname), and name
        # of the actual executable (exename) from the first EXECUTABLE item in
        # toc, which might have come from a COLLECT too (not from an EXE).
        for inm, name, typ in self.toc:
            if typ == "EXECUTABLE":
                self.exename = name
                if self.name is None:
                    self.appname = "Mac%s" % (os.path.splitext(inm)[0],)
                    self.name = os.path.join(SPECPATH, self.appname + ".app")
                else:
                    self.name = os.path.join(SPECPATH, self.name)
                break
        self.__postinit__()

    GUTS = (('toc', _check_guts_eq),  # additional check below
            )

    def check_guts(self, last_build):
        # BUNDLE always needs to be executed, since it will clean the output
        # directory anyway to make sure there is no existing cruft accumulating
        return 1

    def assemble(self):
        if _check_path_overlap(self.name) and os.path.isdir(self.name):
            _rmtree(self.name)
        logger.info("building BUNDLE %s", os.path.basename(self.out))

        # Create a minimal Mac bundle structure
        os.makedirs(os.path.join(self.name, "Contents", "MacOS"))
        os.makedirs(os.path.join(self.name, "Contents", "Resources"))
        os.makedirs(os.path.join(self.name, "Contents", "Frameworks"))

        # Copy icns icon to Resources directory.
        if os.path.exists(self.icon):
            shutil.copy(self.icon, os.path.join(self.name, 'Contents', 'Resources'))
        else:
            logger.warn("icon not found %s" % self.icon)

        # Key/values for a minimal Info.plist file
        info_plist_dict = {"CFBundleDisplayName": self.appname,
                           "CFBundleName": self.appname,
                           # Fix for #156 - 'MacOS' must be in the name - not sure why
                           "CFBundleExecutable": 'MacOS/%s' % os.path.basename(self.exename),
                           "CFBundleIconFile": os.path.basename(self.icon),
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
            # Copy files from cache. This ensures that are used files with relative
            # paths to dynamic library dependencies (@executable_path)
            if typ in ('EXTENSION', 'BINARY'):
                fnm = checkCache(fnm, dist_nm=inm)
            tofnm = os.path.join(self.name, "Contents", "MacOS", inm)
            todir = os.path.dirname(tofnm)
            if not os.path.exists(todir):
                os.makedirs(todir)
            shutil.copy2(fnm, tofnm)

        ## For some hooks copy resource to ./Contents/Resources dir.
        # PyQt4 hook: On Mac Qt requires resources 'qt_menu.nib'.
        # It is copied from dist directory.
        qt_menu_dir = os.path.join(self.name, 'Contents', 'MacOS', 'qt_menu.nib')
        qt_menu_dest = os.path.join(self.name, 'Contents', 'Resources', 'qt_menu.nib')
        if os.path.exists(qt_menu_dir):
            shutil.copytree(qt_menu_dir, qt_menu_dest)

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
            logger.info("TOC found a %s, not a tuple", tpl)
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
            if fd.get(tpl[0], 0):
                del fd[tpl[0]]
        rslt = TOC()
        # return only those things still in fd (preserve order)
        for tpl in self.data:
            if fd.get(tpl[0], 0):
                rslt.append(tpl)
        return rslt

    def __rsub__(self, other):
        rslt = TOC(other)
        return rslt.__sub__(self)

    def intersect(self, other):
        rslt = TOC()
        for tpl in other:
            if self.fltr.get(tpl[0], 0):
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

    GUTS = (('root', _check_guts_eq),
            ('prefix', _check_guts_eq),
            ('excludes', _check_guts_eq),
            ('toc', None),
            )

    def check_guts(self, last_build):
        data = Target.get_guts(self, last_build)
        if not data:
            return True
        stack = [data[0]]  # root
        toc = data[3]  # toc
        while stack:
            d = stack.pop()
            if mtime(d) > last_build:
                logger.info("building %s because directory %s changed",
                            self.outnm, d)
                return True
            for nm in os.listdir(d):
                path = os.path.join(d, nm)
                if os.path.isdir(path):
                    stack.append(path)
        self.data = toc
        return False

    def assemble(self):
        logger.info("building Tree %s", os.path.basename(self.out))
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
                    if xexcludes.get(ext, 0) == 0:
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
        logger.info("%s no change!", self.out)
        return 0


class MERGE(object):
    """
    Merge repeated dependencies from other executables into the first
    execuable. Data and binary files are then present only once and some
    disk space is thus reduced.
    """
    def __init__(self, *args):
        """
        Repeated dependencies are then present only once in the first
        executable in the 'args' list. Other executables depend on the
        first one. Other executables have to extract necessary files
        from the first executable.

        args  dependencies in a list of (Analysis, id, filename) tuples.
              Replace id with the correct filename.
        """
        # The first Analysis object with all dependencies.
        # Any item from the first executable cannot be removed.
        self._main = None

        self._dependencies = {}

        self._id_to_path = {}
        for _, i, p in args:
            self._id_to_path[i] = p

        # Get the longest common path
        self._common_prefix = os.path.dirname(os.path.commonprefix([os.path.abspath(a.scripts[-1][1]) for a, _, _ in args]))
        if self._common_prefix[-1] != os.sep:
            self._common_prefix += os.sep
        logger.info("Common prefix: %s", self._common_prefix)

        self._merge_dependencies(args)

    def _merge_dependencies(self, args):
        """
        Filter shared dependencies to be only in first executable.
        """
        for analysis, _, _ in args:
            path = os.path.abspath(analysis.scripts[-1][1]).replace(self._common_prefix, "", 1)
            path = os.path.splitext(path)[0]
            if path in self._id_to_path:
                path = self._id_to_path[path]
            self._set_dependencies(analysis, path)

    def _set_dependencies(self, analysis, path):
        """
        Syncronize the Analysis result with the needed dependencies.
        """
        for toc in (analysis.binaries, analysis.datas):
            for i, tpl in enumerate(toc):
                if not tpl[1] in self._dependencies.keys():
                    logger.debug("Adding dependency %s located in %s" % (tpl[1], path))
                    self._dependencies[tpl[1]] = path
                else:
                    dep_path = self._get_relative_path(path, self._dependencies[tpl[1]])
                    logger.debug("Referencing %s to be a dependecy for %s, located in %s" % (tpl[1], path, dep_path))
                    analysis.dependencies.append((":".join((dep_path, tpl[0])), tpl[1], "DEPENDENCY"))
                    toc[i] = (None, None, None)
            # Clean the list
            toc[:] = [tpl for tpl in toc if tpl != (None, None, None)]

    # TODO move this function to PyInstaller.compat module (probably improve
    #      function compat.relpath()
    def _get_relative_path(self, startpath, topath):
        start = startpath.split(os.sep)[:-1]
        start = ['..'] * len(start)
        if start:
            start.append(topath)
            return os.sep.join(start)
        else:
            return topath


def TkTree():
    raise SystemExit('TkTree has been removed in PyInstaller 2.0. '
                     'Please update your spec-file. See '
                     'http://www.pyinstaller.org/wiki/MigrateTo2.0 for details')


def TkPKG():
    raise SystemExit('TkPKG has been removed in PyInstaller 2.0. '
                     'Please update your spec-file. See '
                     'http://www.pyinstaller.org/wiki/MigrateTo2.0 for details')


def build(spec, buildpath):
    global SPECPATH, BUILDPATH, WARNFILE, rthooks, SPEC, specnm
    rthooks = _load_data(os.path.join(HOMEPATH, 'support', 'rthooks.dat'))
    SPEC = spec
    SPECPATH, specnm = os.path.split(spec)
    specnm = os.path.splitext(specnm)[0]
    if SPECPATH == '':
        SPECPATH = os.getcwd()
    BUILDPATH = os.path.join(SPECPATH, 'build',
                             "pyi." + sys.platform, specnm)
    # Check and adjustment for build path
    if buildpath != DEFAULT_BUILDPATH:
        bpath = buildpath
        if os.path.isabs(bpath):
            BUILDPATH = bpath
        else:
            BUILDPATH = os.path.join(SPECPATH, bpath)
    WARNFILE = os.path.join(BUILDPATH, 'warn%s.txt' % specnm)
    if not os.path.exists(BUILDPATH):
        os.makedirs(BUILDPATH)
    # Executing the specfile (it's a valid python file)
    execfile(spec)


def __add_options(parser):
    parser.add_option('--buildpath', default=DEFAULT_BUILDPATH,
                      help='Buildpath (default: %default)')
    parser.add_option('-y', '--noconfirm',
                      action="store_true", default=False,
                      help='Remove output directory (default: %s) without '
                      'confirmation' % os.path.join('SPECPATH', 'dist', 'SPECNAME'))
    parser.add_option('--upx-dir', default=None,
                      help='Directory containing UPX (default: search in path)')
    parser.add_option("-a", "--ascii", action="store_true",
                 help="do NOT include unicode encodings "
                      "(default: included if available)")


def main(specfile, buildpath, noconfirm, ascii=False, **kw):
    global config
    global icon, versioninfo, winresource, winmanifest, pyasm
    global HIDDENIMPORTS, NOCONFIRM
    NOCONFIRM = noconfirm

    # Test unicode support.
    if not ascii:
        HIDDENIMPORTS.extend(misc.get_unicode_modules())

    # FIXME: this should be a global import, but can't due to recursive imports
    import PyInstaller.configure as configure
    config = configure.get_config(kw.get('upx_dir'))

    if config['hasRsrcUpdate']:
        from PyInstaller.utils import icon, versioninfo, winresource
        pyasm = bindepend.getAssemblies(sys.executable)
    else:
        pyasm = None

    if config['hasUPX']:
        setupUPXFlags()

    if not config['useELFEXE']:
        EXE.append_pkg = 0

    build(specfile, buildpath)
