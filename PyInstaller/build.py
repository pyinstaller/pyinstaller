#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Build packages using spec files.
"""


import glob
import imp
import os
import pprint
import py_compile
import shutil
import sys
import tempfile
import UserList

from PyInstaller.loader import pyi_archive, pyi_carchive

import PyInstaller.depend.imptracker
import PyInstaller.depend.modules

from PyInstaller import HOMEPATH, CONFIGDIR, PLATFORM, DEFAULT_DISTPATH, DEFAULT_WORKPATH
from PyInstaller.compat import is_win, is_unix, is_aix, is_darwin, is_cygwin
import PyInstaller.compat as compat
import PyInstaller.bindepend as bindepend

from PyInstaller.compat import hashlib
from PyInstaller.depend import dylib
from PyInstaller.utils import misc


import PyInstaller.log as logging
if is_win:
    from PyInstaller.utils import winmanifest


logger = logging.getLogger(__name__)


STRINGTYPE = type('')
TUPLETYPE = type((None,))
UNCOMPRESSED, COMPRESSED = range(2)


# Set of global variables that can be used while processing .spec file.
SPEC = None
SPECPATH = None
DISTPATH = None
WORKPATH = None
WARNFILE = None
NOCONFIRM = None

# Some modules are included if they are detected at build-time or
# if a command-line argument is specified. (e.g. --ascii)
HIDDENIMPORTS = []

rthooks = {}

# place where the loader modules and initialization scripts live
_init_code_path = os.path.join(HOMEPATH, 'PyInstaller', 'loader')
_fake_code_path = os.path.join(HOMEPATH, 'PyInstaller', 'fake')

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
    if is_win:
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
        # the file must not only by stat()-able, but also readable
        if os.access(fnm, os.R_OK):
            return os.stat(fnm)[8]
    except OSError:
        # return 0
        pass
    return 0


def absnormpath(apath):
    return os.path.abspath(os.path.normpath(apath))


def compile_pycos(toc):
    """Given a TOC or equivalent list of tuples, generates all the required
    pyc/pyo files, writing in a local directory if required, and returns the
    list of tuples with the updated pathnames.
    """
    global WORKPATH

    # For those modules that need to be rebuilt, use the build directory
    # PyInstaller creates during the build process.
    basepath = os.path.join(WORKPATH, "localpycos")

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
    Check that path does not overlap with WORKPATH or SPECPATH (i.e.
    WORKPATH and SPECPATH may not start with path, which could be
    caused by a faulty hand-edited specfile)

    Raise SystemExit if there is overlap, return True otherwise
    """
    specerr = 0
    if WORKPATH.startswith(path):
        logger.error('Specfile error: The output path "%s" contains '
                     'WORKPATH (%s)', path, WORKPATH)
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
                           'CONTENTS will be REMOVED! Continue? (y/n) ' % path)
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
    if os.path.altsep:
        pth = pth.replace(os.path.altsep, os.path.sep)
    components = pth.split(os.path.sep)
    sep = os.path.sep

    for i, name in zip(range(0, len(components)), components):
        if name.lower().endswith(".egg"):
            eggpth = sep.join(components[:i + 1])
            if os.path.isfile(eggpth):
                # eggs can also be directories!
                return True
    return False

#--


class Target(object):
    invcnum = 0

    def __init__(self):
        # Get a (per class) unique number to avoid conflicts between
        # toc objects
        self.invcnum = self.__class__.invcnum
        self.__class__.invcnum += 1
        self.out = os.path.join(WORKPATH, 'out%02d-%s.toc' %
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
    """
    Class does analysis of the user's main Python scripts.

    An Analysis has five outputs, all TOCs (Table of Contents) accessed as
    attributes of the analysis.

    scripts
            The scripts you gave Analysis as input, with any runtime hook scripts
            prepended.
    pure
            The pure Python modules.
    binaries
            The extensionmodules and their dependencies. The secondary dependecies
            are filtered. On Windows files from C:\Windows are excluded by default.
            On Linux/Unix only system libraries from /lib or /usr/lib are excluded.
    datas
            Data-file dependencies. These are data-file that are found to be needed
            by modules. They can be anything: plugins, font files, images, translations,
            etc.
    zipfiles
            The zipfiles dependencies (usually .egg files).
    """
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
                 hookspath=None, excludes=None, runtime_hooks=[]):
        """
        scripts
                A list of scripts specified as file names.
        pathex
                An optional list of paths to be searched before sys.path.
        hiddenimport
                An optional list of additional (hidden) modules to include.
        hookspath
                An optional list of additional paths to search for hooks.
                (hook-modules).
        excludes
                An optional list of module or package names (their Python names,
                not path names) that will be ignored (as though they were not found).
        runtime_hooks
                An optional list of scripts to use as users' runtime hooks. Specified
                as file names.
        """
        Target.__init__(self)

        sys._PYI_SETTINGS = {}
        sys._PYI_SETTINGS['scripts'] = scripts

        # Include initialization Python code in PyInstaller analysis.
        self.inputs = [
            os.path.join(_init_code_path, '_pyi_bootstrap.py'),
            os.path.join(_init_code_path, 'pyi_importers.py'),
            os.path.join(_init_code_path, 'pyi_archive.py'),
            os.path.join(_init_code_path, 'pyi_carchive.py'),
            os.path.join(_init_code_path, 'pyi_os_path.py'),
            ]
        for script in scripts:
            if absnormpath(script) in self._old_scripts:
                logger.warn('Ignoring obsolete auto-added script %s', script)
                continue
            if not os.path.exists(script):
                raise ValueError("script '%s' not found" % script)
            self.inputs.append(script)

        self.pathex = []

        # Based on main supplied script - add top-level modules directory to PYTHONPATH.
        # Sometimes the main app script is not top-level module but submodule like 'mymodule.mainscript.py'.
        # In that case PyInstaller will not be able find modules in the directory containing 'mymodule'.
        # Add this directory to PYTHONPATH so PyInstaller could find it.
        for script in scripts:
            script_toplevel_dir = misc.get_path_to_toplevel_modules(script)
            if script_toplevel_dir:
                self.pathex.append(script_toplevel_dir)
                logger.info('Extending PYTHONPATH with %s', script_toplevel_dir)

        # Normalize paths in pathex and make them absolute.
        if pathex:
            self.pathex = [absnormpath(path) for path in pathex]


        self.hiddenimports = hiddenimports or []
        # Include modules detected at build time. Like 'codecs' and encodings.
        self.hiddenimports.extend(HIDDENIMPORTS)

        self.hookspath = hookspath

        # Custom runtime hook files that should be included and started before
        # any existing PyInstaller runtime hooks.
        self.custom_runtime_hooks = runtime_hooks

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

    # TODO implement same functionality as 'assemble()'
    # TODO convert output from 'modulegraph' to PyInstaller format - self.modules.
    # TODO handle hooks properly.
    #def assemble(self):
    def assemble_modulegraph(self):
        """
        New assemble function based on module 'modulegraph' for resolving
        dependencies on Python modules.

        PyInstaller is not able to handle some cases of resolving dependencies.
        Rather try use a module for that than trying to fix current implementation.
        """
        from modulegraph.modulegraph import ModuleGraph
        from modulegraph.find_modules import get_implies, find_needed_modules
        from PyInstaller import hooks

        # Python scripts for analysis.
        scripts = [
            os.path.join(_init_code_path, '_pyi_bootstrap.py'),
        ]

        #tracker = PyInstaller.depend.imptracker.ImportTrackerModulegraph(
                #dirs.keys() + self.pathex, self.hookspath, self.excludes)

        # TODO implement the following to get python modules and extension lists:
        #      process all hooks to get hidden imports and create mapping:
        def collect_implies():
            """
            Collect all hiddenimports from hooks and from modulegraph.
            """
            # Dictionary like
            #   {'mod_name': ['dependent_mod1', dependent_mod2', ...]}
            implies = get_implies()
            # TODO implement getting through hooks
            # TODO use also hook_dir supplied by user
            hook_dir = os.path.dirname(os.path.abspath(hooks.__file__))
            files = glob.glob(hook_dir + os.sep + 'hook-*.py')
            for f in files:
                # Name of the module this hook is for.
                mod_name = os.path.basename(f).lstrip('hook-').rstrip('.py')
                hook_mod_name = 'PyInstaller.hooks.hook-%s' % mod_name
                # Loaded and initialized hook module.
                hook_mod = imp.load_source(hook_mod_name, f)
                if hasattr(hook_mod, 'hiddenimports'):
                    # Extend the list of implies.
                    implies[mod_name] = hook_mod.hiddenimports
            return implies

        #        {'PyQt4.QtGui': ['PyQt4.QtCore', 'sip'], 'another_Mod' ['hidden_import1', 'hidden_import2'], ...}
        #      supply this mapping as 'implies' keyword to
        #        modulegraph.modulegraph.ModuleGraph()
        #      do analysis of scripts - user scripts, pyi_archive, pyi_os_path, pyi_importers, pyi_carchive, _pyi_bootstrap
        #      find necessary rthooks
        #      do analysis of rthooks and add it to modulegraph object
        #      analyze python modules for ctype imports - modulegraph does not do that

        # TODO process other attribute from used pyinstaller hooks.
        # TODO resolve DLL/so/dylib dependencies.
        graph = ModuleGraph(
            path=[_init_code_path] + sys.path,
            implies=collect_implies(),
            debug=0)
        graph = find_needed_modules(graph, scripts=scripts)
        graph.report()


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
            depmanifest.filename = os.path.join(WORKPATH,
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
                d = compat.getcwd()
            d = absnormpath(d)
            pynm, ext = os.path.splitext(base)
            dirs[d] = 1
            pynms.append(pynm)
        ###################################################
        # Initialize importTracker and analyze scripts
        importTracker = PyInstaller.depend.imptracker.ImportTracker(
                dirs.keys() + self.pathex, self.hookspath, self.excludes, workpath=WORKPATH)
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
        zipfiles = []  # zipfiles to bundle - zipped Python .egg files.
        datas = []    # datafiles to bundle
        rthooks = []  # rthooks if needed

        # Include custom rthooks (runtime hooks).
        # The runtime hooks are order dependent. First hooks in the list
        # are executed first.
        # Custom hooks are added before Pyinstaller rthooks and thus they are
        # executed first.
        if self.custom_runtime_hooks:
            logger.info("Including custom run-time hooks")
            # Data structure in format:
            # ('rt_hook_mod_name', '/rt/hook/file/name.py', 'PYSOURCE')
            for hook_file in self.custom_runtime_hooks:
                hook_file = os.path.abspath(hook_file)
                items = (os.path.splitext(os.path.basename(hook_file))[0], hook_file, 'PYSOURCE')
                rthooks.append(items)

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

            datas.extend(mod.pyinstaller_datas)

            if isinstance(mod, PyInstaller.depend.modules.BuiltinModule):
                pass
            elif isinstance(mod, PyInstaller.depend.modules.ExtensionModule):
                binaries.append((mod.__name__, mod.__file__, 'EXTENSION'))
                # allows hooks to specify additional dependency
                # on other shared libraries loaded at runtime (by dlopen)
                binaries.extend(mod.pyinstaller_binaries)
            elif isinstance(mod, (PyInstaller.depend.modules.PkgInZipModule, PyInstaller.depend.modules.PyInZipModule)):
                zipfiles.append(("eggs/" + os.path.basename(str(mod.owner)),
                                 str(mod.owner), 'ZIPFILE'))
            elif isinstance(mod, PyInstaller.depend.modules.NamespaceModule):
                pure.append((modnm,
                             os.path.join(_fake_code_path, 'namespace', '__init__.pyc'),
                             'PYMODULE'))
            else:
                # mf.PyModule instances expose a list of binary
                # dependencies, most probably shared libraries accessed
                # via ctypes. Add them to the overall required binaries.
                binaries.extend(mod.pyinstaller_binaries)
                if modnm != '__main__':
                    pure.append((modnm, mod.__file__, 'PYMODULE'))

        # Add remaining binary dependencies
        binaries.extend(bindepend.Dependencies(binaries,
                                               manifest=depmanifest))
        if is_win:
            depmanifest.writeprettyxml()
        self._check_python_library(binaries)
        if zipfiles:
            scripts.insert(-1, ('_pyi_egg_install.py', os.path.join(_init_code_path, '_pyi_egg_install.py'), 'PYSOURCE'))
        # Add runtime hooks just before the last script (which is
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

    def _check_python_library(self, binaries):
        """
        Verify presence of the Python dynamic library in the binary dependencies.
        Python library is an essential piece that has to be always included.
        """
        python_lib = bindepend.get_python_library_path()

        if python_lib:
            logger.info('Using Python library %s', python_lib)
            # Presence of library in dependencies.
            deps = set()
            for (nm, filename, typ) in binaries:
                if typ == 'BINARY':
                    deps.update([filename])
            # If Python library is missing - append it to dependencies.
            if python_lib not in deps:
                logger.info('Adding Python library to binary dependencies')
                binaries.append((os.path.basename(python_lib), python_lib, 'BINARY'))
        else:
            raise IOError("Python library not found!")


def _findRTHook(modnm):
    rslt = []
    for script in rthooks.get(modnm) or []:
        nm = os.path.basename(script)
        nm = os.path.splitext(nm)[0]
        if os.path.isabs(script):
            path = script
        else:
            path = os.path.join(HOMEPATH, 'PyInstaller', 'loader', 'rthooks', script)
        rslt.append((nm, path, 'PYSOURCE'))
    return rslt


class PYZ(Target):
    """
    Creates a ZlibArchive that contains all pure Python modules.
    """
    typ = 'PYZ'

    def __init__(self, toc, name=None, level=9):
        """
        toc
                A TOC (Table of Contents), normally an Analysis.pure?
        name
                A filename for the .pyz. Normally not needed, as the generated
                name will do fine.
        level
                The Zlib compression level to use. If 0, the zlib module is
                not required.
        """
        Target.__init__(self)
        self.toc = toc
        self.name = name
        if name is None:
            self.name = self.out[:-3] + 'pyz'
        # Level of zlib compression.
        self.level = level
        self.dependencies = compile_pycos(config['PYZ_dependencies'])
        self.__postinit__()

    GUTS = (('name', _check_guts_eq),
            ('level', _check_guts_eq),
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
        logger.info("building PYZ (ZlibArchive) %s", os.path.basename(self.out))
        pyz = pyi_archive.ZlibArchive(level=self.level)
        toc = self.toc - config['PYZ_dependencies']
        pyz.build(self.name, toc)
        _save_data(self.out, (self.name, self.level, self.toc))
        return 1


def cacheDigest(fnm):
    data = open(fnm, "rb").read()
    digest = hashlib.md5(data).digest()
    return digest


def checkCache(fnm, strip=False, upx=False, dist_nm=None):
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
        strip = True
    else:
        strip = False
    if upx:
        upx = True
    else:
        upx = False

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
            fnm = checkCache(fnm, strip=True, upx=False)
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
            strip_options = []
            if is_darwin:
               # The default strip behaviour breaks some shared libraries
               # under Mac OSX.
               # -S = strip only debug symbols.
               strip_options = ["-S"]
            cmd = ["strip"] + strip_options + [cachedfile]

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
            logger.info("Executing - " + ' '.join(cmd))
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


UNCOMPRESSED, COMPRESSED = range(2)


class PKG(Target):
    """
    Creates a CArchive. CArchive is the data structure that is embedded
    into the executable. This data structure allows to include various
    read-only data in a sigle-file deployment.
    """
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
                 strip_binaries=False, upx_binaries=False):
        """
        toc
                A TOC (Table of Contents)
        name
                An optional filename for the PKG.
        cdict
                Dictionary that specifies compression by typecode. For Example,
                PYZ is left uncompressed so that it can be accessed inside the
                PKG. The default uses sensible values. If zlib is not available,
                no compression is used.
        exclude_binaries
                If True, EXTENSIONs and BINARYs will be left out of the PKG,
                and forwarded to its container (usually a COLLECT).
        strip_binaries
                If True, use 'strip' command to reduce the size of binary files.
        upx_binaries
        """
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
            self.cdict = {'EXTENSION': COMPRESSED,
                          'DATA': COMPRESSED,
                          'BINARY': COMPRESSED,
                          'EXECUTABLE': COMPRESSED,
                          'PYSOURCE': COMPRESSED,
                          'PYMODULE': COMPRESSED}
        self.__postinit__()

    GUTS = (('name', _check_guts_eq),
            ('cdict', _check_guts_eq),
            ('toc', _check_guts_toc_mtime),
            ('exclude_binaries', _check_guts_eq),
            ('strip_binaries', _check_guts_eq),
            ('upx_binaries', _check_guts_eq),
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
        logger.info("building PKG (CArchive) %s", os.path.basename(self.name))
        trash = []
        mytoc = []
        seen = {}
        toc = addSuffixToExtensions(self.toc)
        # 'inm'  - relative filename inside a CArchive
        # 'fnm'  - absolute filename as it is on the file system.
        for inm, fnm, typ in toc:
            # Ensure filename 'fnm' is not None or empty string. Otherwise
            # it will fail in case of 'typ' being type OPTION.
            if fnm and not os.path.isfile(fnm) and check_egg(fnm):
                # file is contained within python egg, it is added with the egg
                continue
            if typ in ('BINARY', 'EXTENSION', 'DEPENDENCY'):
                if self.exclude_binaries and typ != 'DEPENDENCY':
                    self.dependencies.append((inm, fnm, typ))
                else:
                    fnm = checkCache(fnm, strip=self.strip_binaries,
                                     upx=(self.upx_binaries and (is_win or is_cygwin)),
                                     dist_nm=inm)
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

        # Bootloader has to know the name of Python library. Pass python libname to CArchive.
        pylib_name = os.path.basename(bindepend.get_python_library_path())
        archive = pyi_carchive.CArchive(pylib_name=pylib_name)

        archive.build(self.name, mytoc)
        _save_data(self.out,
                   (self.name, self.cdict, self.toc, self.exclude_binaries,
                    self.strip_binaries, self.upx_binaries))
        for item in trash:
            os.remove(item)
        return 1


class EXE(Target):
    """
    Creates the final executable of the frozen app.
    This bundles all necessary files together.
    """
    typ = 'EXECUTABLE'

    def __init__(self, *args, **kwargs):
        """
        args
                One or more arguments that are either TOCs Targets.
        kwargs
            Possible keywork arguments:

            console
                On Windows or OSX governs whether to use the console executable
                or the windowed executable. Always True on Linux/Unix (always
                console executable - it does not matter there).
            debug
                Setting to True gives you progress mesages from the executable
                (for console=False there will be annoying MessageBoxes on Windows).
            name
                The filename for the executable.
            exclude_binaries
                Forwarded to the PKG the EXE builds.
            icon
                Windows or OSX only. icon='myicon.ico' to use an icon file or
                icon='notepad.exe,0' to grab an icon resource.
            version
                Windows only. version='myversion.txt'. Use grab_version.py to get
                a version resource from an executable and then edit the output to
                create your own. (The syntax of version resources is so arcane
                that I wouldn't attempt to write one from scratch).
        """
        Target.__init__(self)

        # TODO could be 'append_pkg' removed? It seems not to be used anymore.
        self.append_pkg = kwargs.get('append_pkg', True)

        # Available options for EXE in .spec files.
        self.exclude_binaries = kwargs.get('exclude_binaries', False)
        self.console = kwargs.get('console', True)
        self.debug = kwargs.get('debug', False)
        self.name = kwargs.get('name', None)
        self.icon = kwargs.get('icon', None)
        self.versrsrc = kwargs.get('version', None)
        self.manifest = kwargs.get('manifest', None)
        self.resources = kwargs.get('resources', [])
        self.strip = kwargs.get('strip', False)

        if config['hasUPX']: 
           self.upx = kwargs.get('upx', False)
        else:
           self.upx = False

        # Old .spec format included in 'name' the path where to put created
        # app. New format includes only exename.
        #
        # Ignore fullpath in the 'name' and prepend DISTPATH or WORKPATH.
        # DISTPATH - onefile 
        # WORKPATH - onedir
        if self.exclude_binaries:
            # onedir mode - create executable in WORKPATH.
            self.name = os.path.join(WORKPATH, os.path.basename(self.name))
        else:
            # onefile mode - create executable in DISTPATH.
            self.name = os.path.join(DISTPATH, os.path.basename(self.name))
        
        # Base name of the EXE file without .exe suffix.
        base_name = os.path.basename(self.name)
        if is_win or is_cygwin:
            base_name = os.path.splitext(base_name)[0]
        self.pkgname = base_name + '.pkg'

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
            filename = os.path.join(WORKPATH, specnm + ".exe.manifest")
            self.manifest = winmanifest.create_manifest(filename, self.manifest,
                self.console)
            self.toc.append((os.path.basename(self.name) + ".manifest", filename,
                'BINARY'))
        self.pkg = PKG(self.toc, cdict=kwargs.get('cdict', None),
                       exclude_binaries=self.exclude_binaries,
                       strip_binaries=self.strip, upx_binaries=self.upx,
                       )
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
        return os.path.join('PyInstaller', 'bootloader', PLATFORM, exe)

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
        exe = checkCache(exe, strip=self.strip, upx=self.upx)
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
                mtime(self.name))
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
    """
    On Windows, this provides support for doing in-process COM servers. It is not
    generalized. However, embedders can follow the same model to build a special
    purpose process DLL so the Python support in their app is hidden. You will
    need to write your own dll.
    """
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
    """
    In one-dir mode creates the output folder with all necessary files.
    """
    def __init__(self, *args, **kws):
        """
        args
                One or more arguments that are either TOCs Targets.
        kws
            Possible keywork arguments:

                name
                    The name of the directory to be built.
        """
        Target.__init__(self)
        self.strip_binaries = kws.get('strip', False)

        if config['hasUPX']: 
           self.upx_binaries = kws.get('upx', False)
        else:
           self.upx_binaries = False

        self.name = kws.get('name')
        # Old .spec format included in 'name' the path where to collect files
        # for the created app.
        # app. New format includes only directory name.
        #
        # The 'name' directory is created in DISTPATH and necessary files are
        # then collected to this directory.
        self.name = os.path.join(DISTPATH, os.path.basename(self.name))

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
            if os.pardir in os.path.normpath(inm) or os.path.isabs(inm):
                raise SystemExit('Security-Alert: try to store file outside '
                                 'of dist-directory. Aborting. %r' % inm)
            tofnm = os.path.join(self.name, inm)
            todir = os.path.dirname(tofnm)
            if not os.path.exists(todir):
                os.makedirs(todir)
            if typ in ('EXTENSION', 'BINARY'):
                fnm = checkCache(fnm, strip=self.strip_binaries,
                                 upx=(self.upx_binaries and (is_win or is_cygwin)), 
                                 dist_nm=inm)
            if typ != 'DEPENDENCY':
                shutil.copy(fnm, tofnm)
                try:
                    shutil.copystat(fnm, tofnm)
                except OSError:
                    logger.warn("failed to copy flags of %s", fnm)
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

        # .icns icon for app bundle.
        # Use icon supplied by user or just use the default one from PyInstaller.
        self.icon = kws.get('icon')
        if not self.icon:
            self.icon = os.path.join(os.path.dirname(__file__),
                'bootloader', 'images', 'icon-windowed.icns')
        # Ensure icon path is absolute.
        self.icon = os.path.abspath(self.icon)

        Target.__init__(self)
 
        # .app bundle is created in DISTPATH.
        self.name = kws.get('name', None)
        base_name = os.path.basename(self.name)
        self.name = os.path.join(DISTPATH, base_name)

        self.appname = os.path.splitext(base_name)[0]
        self.version = kws.get("version", "0.0.0")
        self.toc = TOC()
        self.strip = False
        self.upx = False

        self.info_plist = kws.get('info_plist', None)

        for arg in args:
            if isinstance(arg, EXE):
                self.toc.append((os.path.basename(arg.name), arg.name, arg.typ))
                self.toc.extend(arg.dependencies) 
                self.strip = arg.strip
                self.upx = arg.upx 
            elif isinstance(arg, TOC):
                self.toc.extend(arg)
                # TOC doesn't have a strip or upx attribute, so there is no way for us to
                # tell which cache we should draw from.
            elif isinstance(arg, COLLECT):
                self.toc.extend(arg.toc)
                self.strip = arg.strip_binaries
                self.upx = arg.upx_binaries 
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

        # Merge info_plist settings from spec file
        if isinstance(self.info_plist, dict) and self.info_plist:
            info_plist_dict = dict(info_plist_dict.items() + self.info_plist.items())

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
                fnm = checkCache(fnm, strip=self.strip, upx=self.upx, dist_nm=inm)
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
    """
    TOC (Table of Contents) class is a list of tuples of the form (name, path, tytecode).

    typecode    name                   path                        description
    --------------------------------------------------------------------------------------
    EXTENSION   Python internal name.  Full path name in build.    Extension module.
    PYSOURCE    Python internal name.  Full path name in build.    Script.
    PYMODULE    Python internal name.  Full path name in build.    Pure Python module (including __init__ modules).
    PYZ         Runtime name.          Full path name in build.    A .pyz archive (ZlibArchive data structure).
    PKG         Runtime name.          Full path name in build.    A .pkg archive (Carchive data structure).
    BINARY      Runtime name.          Full path name in build.    Shared library.
    DATA        Runtime name.          Full path name in build.    Arbitrary files.
    OPTION      The option.            Unused.                     Python runtime option (frozen into executable).

    A TOC contains various types of files. A TOC contains no duplicates and preserves order.
    PyInstaller uses TOC data type to collect necessary files bundle them into an executable.
    """
    def __init__(self, initlist=None):
        UserList.UserList.__init__(self)
        self.fltr = {}
        if initlist:
            for tpl in initlist:
                self.append(tpl)

    def append(self, tpl):
        try:
            fn = tpl[0]
            if tpl[2] in ["BINARY", "DATA"]:
                # Normalize the case for binary and data files only (to avoid duplicates
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
    """
    This class is a way of creating a TOC (Table of Contents) that describes
    some or all of the files within a directory.
    """
    def __init__(self, root=None, prefix=None, excludes=None):
        """
        root
                The root of the tree (on the build system).
        prefix
                Optional prefix to the names of the target system.
        excludes
                A list of names to exclude. Two forms are allowed:

                    name
                        Files with this basename will be excluded (do not
                        include the path).
                    *.ext
                        Any file with the given extension will be excluded.
        """
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


def build(spec, distpath, workpath, clean_build):
    """
    Build the executable according to the created SPEC file.
    """
    # Set of global variables that can be used while processing .spec file.
    global SPECPATH, DISTPATH, WORKPATH, WARNFILE, rthooks, SPEC, specnm

    rthooks = _load_data(os.path.join(HOMEPATH, 'PyInstaller', 'loader', 'rthooks.dat'))

    # Ensure starting tilde and environment variables get expanded in distpath / workpath.
    # '~/path/abc', '${env_var_name}/path/abc/def'
    distpath = compat.expand_path(distpath)
    workpath = compat.expand_path(workpath)
    SPEC = compat.expand_path(spec)

    SPECPATH, specnm = os.path.split(spec)
    specnm = os.path.splitext(specnm)[0]

    # Add 'specname' to workpath and distpath if they point to PyInstaller homepath.
    if os.path.dirname(distpath) == HOMEPATH:
        distpath = os.path.join(HOMEPATH, specnm, os.path.basename(distpath))
    DISTPATH = distpath
    if os.path.dirname(workpath) == HOMEPATH:
        WORKPATH = os.path.join(HOMEPATH, specnm, os.path.basename(workpath), specnm)
    else:
        WORKPATH = os.path.join(workpath, specnm)

    WARNFILE = os.path.join(WORKPATH, 'warn%s.txt' % specnm)

    # Clean PyInstaller cache (CONFIGDIR) and temporary files (WORKPATH)
    # to be able start a clean build.
    if clean_build:
        logger.info('Removing temporary files and cleaning cache in %s', CONFIGDIR)
        for pth in (CONFIGDIR, WORKPATH):
            if os.path.exists(pth):
                # Remove all files in 'pth'.
                for f in glob.glob(pth + '/*'):
                    # Remove dirs recursively.
                    if os.path.isdir(f):
                        shutil.rmtree(f)
                    else:
                        os.remove(f)

    # Create DISTPATH and WORKPATH if they does not exist.
    for pth in (DISTPATH, WORKPATH):
        if not os.path.exists(WORKPATH):
            os.makedirs(WORKPATH)
 
    # Executing the specfile. The executed .spec file will use DISTPATH and
    # WORKPATH values.
    execfile(spec)


def __add_options(parser):
    parser.add_option("--distpath", metavar="DIR",
                default=DEFAULT_DISTPATH,
                 help='Where to put the bundled app (default: %default)')
    parser.add_option('--workpath', default=DEFAULT_WORKPATH,
                      help='Where to put all the temporary work files, .log, .pyz and etc. (default: %default)')
    parser.add_option('-y', '--noconfirm',
                      action="store_true", default=False,
                      help='Replace output directory (default: %s) without '
                      'asking for confirmation' % os.path.join('SPECPATH', 'dist', 'SPECNAME'))
    parser.add_option('--upx-dir', default=None,
                      help='Path to UPX utility (default: search the execution path)')
    parser.add_option("-a", "--ascii", action="store_true",
                 help="Do not include unicode encoding support "
                      "(default: included if available)")
    parser.add_option('--clean', dest='clean_build', action='store_true', default=False,
                 help='Clean PyInstaller cache and remove temporary files '
                      'before building.')


def main(pyi_config, specfile, noconfirm, ascii=False, **kw):
    # Set of global variables that can be used while processing .spec file.
    global config
    global icon, versioninfo, winresource, winmanifest, pyasm
    global HIDDENIMPORTS, NOCONFIRM
    NOCONFIRM = noconfirm

    # Test unicode support.
    if not ascii:
        HIDDENIMPORTS.extend(misc.get_unicode_modules())

    # FIXME: this should be a global import, but can't due to recursive imports
    # If configuration dict is supplied - skip configuration step.
    if pyi_config is None:
        import PyInstaller.configure as configure
        config = configure.get_config(kw.get('upx_dir'))
    else:
        config = pyi_config

    if config['hasRsrcUpdate']:
        from PyInstaller.utils import icon, versioninfo, winresource
        pyasm = bindepend.getAssemblies(sys.executable)
    else:
        pyasm = None

    if config['hasUPX']:
        setupUPXFlags()

    build(specfile, kw.get('distpath'), kw.get('workpath'), kw.get('clean_build'))
