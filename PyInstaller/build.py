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
import importlib
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

# TODO: explain why this doesn't use os.path.getmtime() ?
def mtime(fnm):
    try:
        return os.stat(fnm)[8]
    except:
        return 0


def absnormpath(apath):
    return os.path.abspath(os.path.normpath(apath))


def compile_pycos(toc):
    """
    Given a TOC or equivalent list of tuples, generates all the required
    pyc/pyo files, writing in a local directory if required, and returns the
    list of tuples with the updated pathnames.
    
    In the old system using ImpTracker, the generated TOC of "pure" modules
    already contains paths to nm.pyc or nm.pyo and it is only necessary
    to check that these files are not older than the source.
    In the new system using ModuleGraph, the path given is to nm.py
    and we do not know if nm.pyc/.pyo exists. The following logic works
    with both (so if at some time modulegraph starts returning filenames
    of .pyc, it will cope).

    If PyInstaller is running optimized ("python -O pyinstaller...")
    we will look first for .pyo files; otherwise look for .pyc ones.
    """
    global WORKPATH

    # For those modules that need to be rebuilt, use the build directory
    # PyInstaller creates during the build process.
    basepath = os.path.join(WORKPATH, "localpycos")
    # Copy everything from toc to this new TOC, possibly unchanged.
    new_toc = []
    for (nm, fnm, typ) in toc:
        if typ != 'PYMODULE':
            new_toc.append((nm, fnm, typ))
            continue

        if fnm.endswith('.py') :
            # we are given a source path, determine the object path if any
            src_fnm = fnm
            # assume we want pyo only when now running -O or -OO
            obj_fnm = src_fnm + ('o' if sys.flags.optimize else 'c')
            if not os.path.exists(obj_fnm) :
                # alas that one is not there so assume the other choice
                obj_fnm = src_fnm + ('c' if sys.flags.optimize else 'o')
        else:
            # fnm is not "name.py" so assume we are given name.pyc/.pyo
            obj_fnm = fnm # take that namae to be the desired object
            src_fnm = fnm[:-1] # drop the 'c' or 'o' to make a source name

        # We need to perform a build ourselves if obj_fnm doesn't exist,
        # or if src_fnm is newer than obj_fnm, or if obj_fnm was created
        # by a different Python version.
        # TODO: explain why this does read()[:4] (reading all the file)
        # instead of just read(4)? Yes for many a .pyc file, it is all
        # in one sector so there's no difference in I/O but still it
        # seems inelegant to copy it all then subscript 4 bytes.
        needs_compile = ( (mtime(src_fnm) > mtime(obj_fnm) )
                          or
                          (open(obj_fnm, 'rb').read()[:4] != imp.get_magic())
                        )
        if needs_compile:
            try:
                # TODO: there should be no need to repeat the compile,
                # because ModuleGraph does a compile and stores the result
                # in the .code member of the graph node. Should be possible
                # to get the node and write the code to obj_fnm
                py_compile.compile(src_fnm, obj_fnm)
                logger.debug("compiled %s", src_fnm)
            except IOError:
                # If we're compiling on a system directory, probably we don't
                # have write permissions; thus we compile to a local directory
                # and change the TOC entry accordingly.
                ext = os.path.splitext(obj_fnm)[1]

                if "__init__" not in obj_fnm:
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

                obj_fnm = os.path.join(leading, mod_name + ext)
                # TODO see above regarding read()[:4] versus read(4)
                needs_compile = (mtime(src_fnm) > mtime(obj_fnm)
                                 or
                                 open(obj_fnm, 'rb').read()[:4] != imp.get_magic())
                if needs_compile:
                    # TODO see above regarding using node.code
                    py_compile.compile(src_fnm, fnm)
                    logger.debug("compiled %s", src_fnm)
        # if we get to here, obj_fnm is the path to the compiled module nm.py
        new_toc.append((nm, obj_fnm, typ))

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


#--- functions for checking guts ---

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
        _init_code_path = os.path.join(HOMEPATH, 'PyInstaller', 'loader')
        self.inputs = [
            os.path.join(_init_code_path, '_pyi_bootstrap.py'),
            os.path.join(_init_code_path, 'pyi_importers.py'),
            os.path.join(_init_code_path, 'pyi_archive.py'),
            os.path.join(_init_code_path, 'pyi_carchive.py'),
            os.path.join(_init_code_path, 'pyi_os_path.py'),
            ]
        self.loader_path = os.path.join(HOMEPATH, 'PyInstaller', 'loader')
        #TODO: store user scripts in separate variable from init scripts,
        # see TODO (S) below
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
        # Include modules detected when parsing options,l ike 'codecs' and encodings.
        self.hiddenimports.extend(HIDDENIMPORTS)

        self.hookspath = hookspath

        # Custom runtime hook files that should be included and started before
        # any existing PyInstaller runtime hooks.
        self.custom_runtime_hooks = runtime_hooks

        self.excludes = excludes
        self.scripts = TOC()
        self.pure = {'toc': TOC(), 'code': {}}
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

    def _format_hook_datas(self, hook):
        """
        hook.datas is a list of globs of files or
        directories to bundle as datafiles. For each
        glob, a destination directory is specified.
        """
        datas = []

        def _visit((base, dest_dir, datas), dirname, names):
            """
            Format whole directory tree from 'datas'.
            """
            for fn in names:
                fn = os.path.join(dirname, fn)
                if os.path.isfile(fn):
                    datas.append((dest_dir + fn[len(base) + 1:], fn, 'DATA'))

        for g, dest_dir in getattr(hook, 'datas', []):
            if dest_dir:
                dest_dir += os.sep
            for fn in glob.glob(g):
                if os.path.isfile(fn):
                    datas.append((dest_dir + os.path.basename(fn), fn, 'DATA'))
                else:
                    os.path.walk(fn, _visit, (os.path.dirname(fn), dest_dir, datas))
        return datas

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
        self.pure = {'toc': TOC(pure), 'code': {}}
        self.binaries = TOC(binaries)
        self.zipfiles = TOC(zipfiles)
        self.datas = TOC(datas)
        self.hiddenimports = hiddenimports
        return False

    def assemble(self):
        logger.info("running Analysis %s", os.path.basename(self.out))
        # Get paths to Python and, in Windows, the manifest.
        python = sys.executable
        if not is_win:
            # Linux/MacOS: get a real, non-link path to the running Python executable.            
            while os.path.islink(python):
                python = os.path.join(os.path.dirname(python), os.readlink(python))
            depmanifest = None
        else:
            # Windows: no links, but "manifestly" need this:
            depmanifest = winmanifest.Manifest(type_="win32", name=specnm,
                                               processorArchitecture=winmanifest.processor_architecture(),
                                               version=(1, 0, 0, 0))
            depmanifest.filename = os.path.join(WORKPATH,
                                                specnm + ".exe.manifest")

        # We record "binaries" separately from the modulegraph, as there
        # is no way to record those dependencies in the graph. These include
        # the python executable and any binaries added by hooks later.
        # "binaries" are not the same as "extensions" which are .so or .dylib
        # that are found and recorded as extension nodes in the graph.
        # Reset seen variable before running bindepend. We use bindepend only for
        # the python executable.
        bindepend.seen = {}
        # Add Python's dependencies first.
        # This ensures that its assembly depencies under Windows get pulled in
        # first, so that .pyd files analyzed later which may not have their own
        # manifest and may depend on DLLs which are part of an assembly
        # referenced by Python's manifest, don't cause 'lib not found' messages
        self.binaries.extend(bindepend.Dependencies([('', python, '')],
                                               manifest=depmanifest)[1:])
                
        # Instantiate a ModuleGraph. The class is defined at end of this module.
        # The argument is the set of paths to use for imports: sys.path,
        # plus our loader, plus other paths from e.g. --path option).
        self.graph = PyiModuleGraph(sys.path + [self.loader_path] + self.pathex)
        
        # Graph the first script in the analysis, and save its node to use as
        # the "caller" node for all others. This gives a connected graph rather than
        # a collection of unrelated trees, one for each of self.inputs.
        # The list of scripts, starting with our own bootstrap ones, is in
        # self.inputs, each as a normalized pathname.
        
        # TODO: (S) in __init__ the input scripts should be saved separately from the
        # pyi-loader set. TEMP: assume the first/only user script is self.inputs[5]
        script = self.inputs[5]
        logger.info("Analyzing %s", script)
        top_node = self.graph.run_script(script)
        # list to hold graph nodes of loader scripts and runtime hooks in use order        
        priority_scripts = [] 
        # With a caller node in hand, import all the loader set as called by it.
        # The old Analysis checked that the script existed and raised an error,
        # but now just assume that if it does not, Modulegraph will raise error.
        # Save the graph nodes of each in sequence.
        for script in self.inputs[:5] :
            logger.info("Analyzing %s", script)
            priority_scripts.append( self.graph.run_script(script, top_node) )
        # And import any remaining user scripts as if called by the first one.
        for script in self.inputs[6:] :
            logger.info("Analyzing %s", script)
            node = self.graph.run_script(script,top_node)

        # Analyze the script's hidden imports (named on the command line)
        for modnm in self.hiddenimports:
            if self.graph.findNode(modnm) is not None :
                logger.info("Hidden import %r has been found otherwise", modnm)
                continue
            logger.info("Analyzing hidden import %r", modnm)
            # ModuleGraph throws Import Error if import not found
            try :
                node = self.graph.import_hook(modnm, top_node)
            except :
                logger.error("Hidden import %r not found", modnm)

        # Process custom runtime hooks (from --runtime-hook options).
        # The runtime hooks are order dependent. First hooks in the list
        # are executed first. Put their graph nodes at the head of the
        # priority_scripts list Pyinstaller-defined rthooks and
        # thus they are executed first.

        # First priority script has to be '_pyi_bootstrap' and rthooks after
        # this script. - _pyi_bootstrap is at position 0. First rthook should
        # be at position 1.
        RTH_START_POSITION = 1
        rthook_next_position = RTH_START_POSITION

        if self.custom_runtime_hooks:
            for hook_file in self.custom_runtime_hooks:
                logger.info("Including custom run-time hook %r", hook_file)                
                hook_file = os.path.abspath(hook_file)
                # Not using "try" here because the path is supposed to
                # exist, if it does not, the raised error will explain.
                priority_scripts.insert( RTH_START_POSITION, self.graph.run_script(hook_file, top_node) )
                rthook_next_position += 1

        # Find runtime hooks that are implied by packages already imported.
        # Get a temporary TOC listing all the scripts and packages graphed
        # so far. Assuming that runtime hooks apply only to modules and packages.
        temp_toc, code_dict = self.graph.make_a_TOC(['PYMODULE','PYSOURCE'])
        self.pure['code'].update(code_dict)
        logger.info("Looking for standard run-time hooks")
        for (name, path, typecode) in temp_toc :
            for (hook, path, typecode) in _findRTHook(name) :
                logger.info("Including run-time hook %r", hook)
                priority_scripts.insert(
                    rthook_next_position,
                    self.graph.run_script(path, top_node)
                )
        # priority_scripts is now a list of the graph nodes of custom runtime
        # hooks, then regular runtime hooks, then the PyI loader scripts.
        # Further on, we will make sure they end up at the front of self.scripts 

        # KLUDGE? If any script analyzed so far has imported "site" then,
        # when in the next step we call hook_site.py, it will replace
        # the code of the site node with the code of fake/fake-site.py. 
        # But we also need to let Modulegraph know about any imports from
        # that fake_site module and replace found imports of the 'site' module.
        # TODO I think the following code could be removed. Updating dependencies
        #      found in 'site' is done in PyInstaller.depend.modules.FakeModule.retarget()
        #node = self.graph.findNode('site')
        #if node is not None :
            #self.graph.run_script(
                #os.path.join(HOMEPATH, 'PyInstaller', 'fake', 'fake-site.py'),
                #top_node)

        # Now find regular hooks and execute them. Get a new TOC, in part
        # because graphing a runtime hook might have added some names, but
        # also because regular hooks can apply to extensions and builtins.
        temp_toc, code_dict = self.graph.make_a_TOC(['PYMODULE','PYSOURCE','BUILTIN','EXTENSION'])
        self.pure['code'].update(code_dict)
        for (imported_name, path, typecode) in temp_toc :
            try:
                hook_name = 'hook-' + imported_name
                hook_name_space = importlib.import_module('PyInstaller.hooks.' + hook_name)
            except ImportError:
                continue
            # TODO: move the following to a function like imptracker.handle_hook
            logger.info('Processing hook %s' % hook_name)
            from_node = self.graph.findNode(imported_name)
            # hook_name_space represents the code of "hook-imported_name.py"
            if hasattr(hook_name_space,'hiddenimports') :
                # push hidden imports into the graph, as if imported from name
                for item in hook_name_space.hiddenimports :
                    to_node = self.graph.findNode(item)
                    if to_node is None :
                        self.graph.import_hook(item,from_node)
                    #else :
                        #print('hidden import {0} found otherwise'.format(item))
            if hasattr(hook_name_space,'datas') :
                # Add desired data files to our datas TOC
                self.datas.extend(self._format_hook_datas(hook_name_space))
            if hasattr(hook_name_space,'hook'):
                # Process a hook(mod) function. Create a Module object as its API.
                # TODO: it won't be called "FakeModule" later on
                mod = PyInstaller.depend.modules.FakeModule(imported_name,self.graph)
                mod = hook_name_space.hook(mod)
                for item in mod._added_imports :
                    # as with hidden imports, add to graph as called by imported_name
                    self.graph.run_script(item,from_node)
                for item in mod._added_binaries :
                    self.binaries.append(item) # supposed to be TOC form (n,p,'BINARY')
                for item in mod._deleted_imports :
                    # Remove the graph link between the hooked module and item.
                    # This removes the 'item' node from the graph if no other
                    # links go to it (no other modules import it)
                    self.graph.removeReference(mod.node,item)
        
        # Extract the nodes of the graph as TOCs for further processing.
        # Initialize the scripts list with priority scripts in the proper order.
        self.scripts = self.graph.nodes_to_TOC(priority_scripts)
        # Put all other script names into the TOC after them. (The rthooks names
        # will be found again, but TOC.append skips duplicates.)
        self.scripts, code_dict = self.graph.make_a_TOC(['PYSOURCE'], self.scripts)
        self.pure['code'].update(code_dict)
        # Extend the binaries list with all the Extensions modulegraph has found.
        self.binaries, code_dict = self.graph.make_a_TOC(['EXTENSION', 'BINARY'],self.binaries)
        self.pure['code'].update(code_dict)
        # Fill the "pure" list with modules.
        self.pure['toc'], code_dict =  self.graph.make_a_TOC(['PYMODULE'])
        self.pure['code'].update(code_dict)

        # Ensure we have .pyc/.pyo object files for all PYMODULE in pure
        #self.pure = TOC(compile_pycos(self.pure))

        # TODO: ImpTracker could flag a module as residing in a zip file (because an
        # egg that had not yet been installed??) and the old code would do this:      
        # scripts.insert(-1, ('_pyi_egg_install.py',
        #     os.path.join(_init_code_path, '_pyi_egg_install.py'), 'PYSOURCE'))
        # It appears that Modulegraph will expand an uninstalled egg but need test
        self.zipfiles = TOC()
        # Copied from original code
        if is_win:
            depmanifest.writeprettyxml()
        # Get the saved details of a prior run, if any. Would not exist if
        # the user erased the work files, or gave a different --workpath
        # or specified --clean.
        try:
            oldstuff = _load_data(self.out)
        except:
            oldstuff = None

        # Collect the work-product of this run
        newstuff = tuple([getattr(self, g[0]) for g in self.GUTS])
        # If there was no previous, or if it is different, save the new
        if oldstuff != newstuff:
            # Save all the new stuff to avoid regenerating it later, maybe
            _save_data(self.out, newstuff)
            # Write warnings about missing modules. Get them from the graph
            # and use the graph to figure out who tried to import them.
            # TODO: previously we could say whether an import was top-level,
            # deferred (in a def'd function) or conditional (in an if stmt).
            # That information is not available from ModuleGraph at this time.
            # When that info is available change this code to write one line for
            # each importer-name, with type of import for that importer
            # "no module named foo conditional/deferred/toplevel importy by bar"
            miss_toc, code_dict = self.graph.make_a_TOC(['MISSING'])
            self.pure['code'].update(code_dict)
            if len(miss_toc) : # there are some missing modules
                wf = open(WARNFILE, 'w')
                for (n, p, t) in miss_toc :
                    importer_names = self.graph.importer_names(n)
                    wf.write( 'no module named '
                              + n
                              + ' - imported by '
                              + ', '.join(importer_names)
                              + '\n'
                              )
                wf.close()
                logger.info("Warnings written to %s", WARNFILE)
            return 1
        else :
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

    def __init__(self, toc_dict, name=None, level=9):
        """
        toc_dict
            toc_dict['toc']
                A TOC (Table of Contents), normally an Analysis.pure['toc']?
            toc_dict['code']
                A dict of module code objects from ModuleGraph.
        name
                A filename for the .pyz. Normally not needed, as the generated
                name will do fine.
        level
                The Zlib compression level to use. If 0, the zlib module is
                not required.
        """
        Target.__init__(self)
        self.toc = toc_dict['toc']
        # Use code objects directly from ModuleGraph to speed up PyInstaller.
        self.code_dict = toc_dict['code']
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
        pyz = pyi_archive.ZlibArchive(level=self.level, code_dict=self.code_dict)
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
            tofnm = os.path.join(self.name, inm)
            todir = os.path.dirname(tofnm)
            if not os.path.exists(todir):
                os.makedirs(todir)
            if typ in ('EXTENSION', 'BINARY'):
                fnm = checkCache(fnm, strip=self.strip_binaries,
                                 upx=(self.upx_binaries and (is_win or is_cygwin)), 
                                 dist_nm=inm)
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

# ----------------------------------------------------------------
'''
Define a modified ModuleGraph that can return its contents as
a TOC and in other ways act like the old ImpTracker.
TODO: This class, along with TOC and Tree should be in a separate module.

For reference, the ModuleGraph node types and their contents:

  nodetype       identifier       filename		    

 Script         full path to .py   full path to .py
 SourceModule     basename         full path to .py    
 BuiltinModule    basename         None
 CompiledModule   basename         full path to .pyc    
 Extension        basename         full path to .so
 MissingModule    basename         None
 Package          basename         full path to __init__.py
        packagepath is ['path to package']
        globalnames is set of global names __init__.py defines

The main extension here over ModuleGraph is a method to extract nodes
from the flattened graph and return them as a TOC, or added to a TOC.
Other added methods look up nodes by identifier and return facts
about them, replacing what the old ImpTracker list could do.
'''
# ----------------------------------------------------------------
from modulegraph.modulegraph import ModuleGraph
class PyiModuleGraph(ModuleGraph):
    def __init__ (self, *args) :
        super(PyiModuleGraph, self).__init__(*args)
        # Dict to map ModuleGraph node types to TOC typecodes
        self.typedict = {
            'Module' : 'PYMODULE',
            'SourceModule' : 'PYMODULE',
            'CompiledModule' : 'PYMODULE',
            'Package' : 'PYMODULE',
            'Extension' : 'EXTENSION',
            'Script' : 'PYSOURCE',
            'BuiltinModule' : 'BUILTIN',
            'MissingModule' : 'MISSING',
            'does not occur' : 'BINARY'
            }
    
    # Return the name, path and type of selected nodes as a TOC, or appended
    # to a TOC. The selection is via a list of PyInstaller TOC typecodes.
    # If that list is empty we return the complete flattened graph as a TOC
    # with the ModuleGraph note types in place of typecodes -- meant for
    # debugging only. Normally we return ModuleGraph nodes whose types map
    # to the requested PyInstaller typecode(s) as indicated in the typedict.
    #
    # We use the ModuleGraph (really, ObjectGraph) flatten() method to
    # scan all the nodes. This is patterned after ModuleGraph.report().

    def make_a_TOC(self, typecode = [], existing_TOC = None ):
        result = existing_TOC or TOC()
        # Keep references to module code objects constructed by ModuleGraph
        # to avoid writting .pyc/pyo files to hdd.
        code_dict = {}
        for node in self.flatten() :
            # get node type e.g. Script
            mg_type = type(node).__name__
            if mg_type is None:
                continue # some nodes are not typed?
            # translate to the corresponding TOC typecode, or leave as-is
            toc_type = self.typedict.get(mg_type, mg_type)
            # Does the caller care about the typecode?
            if len(typecode) :
                # Caller cares, so if there is a mismatch, skip this one
                if not (toc_type in typecode) :
                    continue
            # else: caller doesn't care, return ModuleGraph type in typecode
            # Extract the identifier and a path if any.
            if mg_type == "Script" :
                # for Script nodes only, identifier is a whole path
                (name, ext) = os.path.splitext(node.filename)
                name = os.path.basename(name)
            else:
                name = node.identifier
            path = node.filename if node.filename is not None else ''
            # TOC.append the data. This checks for a pre-existing name
            # and skips it if it exists.
            result.append( (name, path, toc_type) )
            # Keep references to module code objects constructed by ModuleGraph
            # to avoid compiling and writting .pyc/pyo files to hdd.
            if node.code:
                code_dict[name] = node.code
        return result, code_dict
    
    # Given a list of nodes, create a TOC representing those nodes.
    # This is mainly used to initialize a TOC of scripts with the
    # ones that are runtime hooks. The process is almost the same as
    # make_a_TOC, but the caller guarantees the nodes are
    # valid, so minimal checking.
    def nodes_to_TOC(self, node_list, existing_TOC = None ):
        result = existing_TOC or TOC()
        for node in node_list:
            mg_type = type(node).__name__
            toc_type = self.typedict[mg_type]
            if mg_type == "Script" :
                (name, ext) = os.path.splitext(node.filename)
                name = os.path.basename(name)
            else:
                name = node.identifier
            path = node.filename if node.filename is not None else ''
            result.append( (name, path, toc_type) )
        return result

    # Return true if the named item is in the graph as a BuiltinModule node.
    # The passed name is a basename.
    def is_a_builtin(self, name) :
        node = self.findNode(name)
        if node is None : return False
        return type(node).__name__ == 'BuiltinModule'

    # Return a list of the names that import a given name. Basically
    # just get the iterator for incoming-edges and return the
    # identifiers from the nodes it reports.
    def importer_names(self, name) :
        node = self.findNode(name)
        if node is None : return []
        _, iter_inc = self.get_edges(node)
        return [importer.identifier for importer in iter_inc]
            
# ----------------------------------------------------------------
# End PyiModuleGraph
# ----------------------------------------------------------------


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
    # TEMP-REMOVE 2 lines
    global DEBUG # save debug flag for temp use
    DEBUG = kw['debug']
    
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
