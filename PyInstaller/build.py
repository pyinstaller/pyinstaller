#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Build packages using spec files.

NOTE: All global variables, classes and imported modules create API
      for .spec files.
"""


import glob
import hashlib
import os
import platform
import shutil
import sys
import tempfile


# Relative imports to PyInstaller modules.
from . import HOMEPATH, CONFIGDIR, PLATFORM, DEFAULT_DISTPATH, DEFAULT_WORKPATH
from . import compat
from . import log as logging
import collections
from .utils.misc import absnormpath
from .compat import is_py2, is_win, is_darwin, is_cygwin, EXTENSION_SUFFIXES, PYDYLIB_NAMES
from .compat import importlib_load_source
from .depend import bindepend
from .depend import dylib
from .depend.analysis import PyiModuleGraph, TOC, FakeModule, get_bootstrap_modules
from .depend.utils import create_py3_base_library, is_path_to_egg
from .loader import pyi_archive, pyi_carchive
from .utils import misc
from .utils.misc import save_py_data_struct, load_py_data_struct
from .lib.modulegraph.find_modules import get_implies

if is_win:
    from .utils.win32 import icon, versioninfo, winmanifest, winresource


logger = logging.getLogger(__name__)

STRINGTYPE = type('')
TUPLETYPE = type((None,))
UNCOMPRESSED = 0
COMPRESSED = 1

rthooks = {}

# place where the loader modules and initialization scripts live
_init_code_path = os.path.join(HOMEPATH, 'PyInstaller', 'loader')


_MISSING_BOOTLOADER_ERRORMSG = """
Fatal error: PyInstaller does not include a pre-compiled bootloader for your
platform. See <http://pythonhosted.org/PyInstaller/#building-the-bootloader>
for more details and instructions how to build the bootloader.
"""


def _old_api_error(obj_name):
    """
    Cause PyInstall to exit when .spec file uses old api.
    :param obj_name: Name of the old api that is no longer suppored.
    """
    raise SystemExit('%s has been removed in PyInstaller 2.0. '
                     'Please update your spec-file. See '
                     'http://www.pyinstaller.org/wiki/MigrateTo2.0 '
                     'for details' % obj_name)


def _save_data(filename, data):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    outf = open(filename, 'w')
    pprint.pprint(data, outf)
    outf.close()


def _load_data(filename):
    return eval(open(filename, 'rU').read())


# TODO find better place for function.
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


# TODO find better place for function.
def add_suffix_to_extensions(toc):
    """
    Returns a new TOC with proper library suffix for EXTENSION items.
    """
    new_toc = TOC()
    for inm, fnm, typ in toc:
        if typ == 'EXTENSION':
            # Use first suffix from the Python list of suffixes
            # for C extensions.
            inm = inm + EXTENSION_SUFFIXES[0]

        elif typ == 'DEPENDENCY':
            # Use the suffix from the filename.
            # TODO Verify what extensions are by DEPENDENCIES.
            binext = os.path.splitext(fnm)[1]
            if not os.path.splitext(inm)[1] == binext:
                inm = inm + binext
        new_toc.append((inm, fnm, typ))
    return new_toc


#--- functions for checking guts ---
# NOTE: By GUTS it is meant intermediate files and data structures that
# PyInstaller creates for bundling files and creating final executable.


def _check_guts_eq(attr, old, new, last_build):
    """
    rebuild is required if values differ
    """
    if old != new:
        logger.info("Building because %s changed", attr)
        return True
    return False


def _check_guts_toc_mtime(attr, old, toc, last_build, pyc=0):
    """
    rebuild is required if mtimes of files listed in old toc are newer
    than ast_build

    if pyc=1, check for .py files, too
    """
    for (nm, fnm, typ) in old:
        if misc.mtime(fnm) > last_build:
            logger.info("Building because %s changed", fnm)
            return True
        elif pyc and misc.mtime(fnm[:-1]) > last_build:
            logger.info("Building because %s changed", fnm[:-1])
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
    from .config import CONF
    specerr = 0
    if CONF['workpath'].startswith(path):
        logger.error('Specfile error: The output path "%s" contains '
                     'WORKPATH (%s)', path, CONF['workpath'])
        specerr += 1
    if CONF['specpath'].startswith(path):
        logger.error('Specfile error: The output path "%s" contains '
                     'SPECPATH (%s)', path, CONF['specpath'])
        specerr += 1
    if specerr:
        raise SystemExit('Error: Please edit/recreate the specfile (%s) '
                         'and set a different output name (e.g. "dist").'
                         % CONF['spec'])
    return True


def _rmtree(path):
    """
    Remove directory and all its contents, but only after user confirmation,
    or if the -y option is set
    """
    from .config import CONF
    if CONF['noconfirm']:
        choice = 'y'
    elif sys.stdout.isatty():
        choice = compat.stdin_input('WARNING: The output directory "%s" and ALL ITS '
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


class Target(object):
    invcnum = 0

    def __init__(self):
        from .config import CONF
        # Get a (per class) unique number to avoid conflicts between
        # toc objects
        self.invcnum = self.__class__.invcnum
        self.__class__.invcnum += 1
        self.out = os.path.join(CONF['workpath'], 'out%02d-%s.toc' %
                                (self.invcnum, self.__class__.__name__))
        self.outnm = os.path.basename(self.out)
        self.dependencies = TOC()

    def __postinit__(self):
        logger.info("checking %s", self.__class__.__name__)
        if self.check_guts(misc.mtime(self.out)):
            self.assemble()

    GUTS = []

    def check_guts(self, last_build):
        pass

    def get_guts(self, last_build, missing='missing or bad'):
        """
        returns None if guts have changed
        """
        try:
            data = load_py_data_struct(self.out)
        except:
            logger.info("Building because %s %s", os.path.basename(self.out), missing)
            return None

        if len(data) != len(self.GUTS):
            logger.info("Building because %s is bad", self.outnm)
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

    def __init__(self, scripts, pathex=None, hiddenimports=None,
                 hookspath=None, excludes=None, runtime_hooks=[], cipher=None):
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
        super(Analysis, self).__init__()
        from .config import CONF

        self.inputs = []
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
            self.pathex += [absnormpath(path) for path in pathex]


        self.hiddenimports = hiddenimports or []
        # Include modules detected when parsing options, like 'codecs' and encodings.
        self.hiddenimports.extend(CONF['hiddenimports'])

        self.hookspath = hookspath

        # Custom runtime hook files that should be included and started before
        # any existing PyInstaller runtime hooks.
        self.custom_runtime_hooks = runtime_hooks

        if cipher:
            logger.info('Will encrypt Python bytecode with key: %s', cipher.key)

            # Create a Python module which contains the decryption key which will
            # be used at runtime by pyi_crypto.PyiBlockCipher.
            pyi_crypto_key_path = os.path.join(CONF['workpath'], 'pyi_crypto_key.py')

            with open(pyi_crypto_key_path, 'w') as f:
                f.write('key = %r\n' % cipher.key)

            # Compile the module so that it ends up in the CArchive and can be
            # imported by the bootstrap script.
            import py_compile
            py_compile.compile(pyi_crypto_key_path)

            logger.info('Adding dependency on pyi_crypto and pyi_crypto_key')

            from PyInstaller.loader import pyi_crypto
            self.hiddenimports.append(pyi_crypto.HIDDENIMPORT)

            pyi_crypto_path = os.path.join(_init_code_path, 'pyi_crypto.py')

            CONF['PYZ_dependencies'].append(('pyi_crypto', pyi_crypto_path + 'c', 'PYMODULE'))
            CONF['PYZ_dependencies'].append(('pyi_crypto_key', pyi_crypto_key_path + 'c', 'PYMODULE'))

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
            ('pure', lambda *args: _check_guts_toc_mtime(*args, **{'pyc': 1})),
            ('binaries', _check_guts_toc_mtime),
            ('zipfiles', _check_guts_toc_mtime),
            ('datas', _check_guts_toc_mtime),
            ('hiddenimports', _check_guts_eq),
            )

    # TODO Refactor to prohibit empty target directories. As the docstring
    #below documents, this function currently permits the second item of each
    #2-tuple in "hook.datas" to be the empty string, in which case the target
    #directory defaults to the source directory's basename. However, this
    #functionality is very fragile and hence bad. Instead:
    #
    #* An exception should be raised if such item is empty.
    #* All hooks currently passing the empty string for such item (e.g.,
    #  "hooks/hook-babel.py", "hooks/hook-matplotlib.py") should be refactored
    #  to instead pass such basename.
    def _format_hook_datas(self, hook):
        """
        Convert the passed `hook.datas` list to a list of `TOC`-style 3-tuples.

        `hook.datas` is a list of 2-tuples whose:

        * First item is either:
          * A glob matching only the absolute paths of source non-Python data
            files.
          * The absolute path of a directory containing only such files.
        * Second item is either:
          * The relative path of the target directory into which such files will
            be recursively copied.
          * The empty string. In such case, if the first item was:
            * A glob, such files will be recursively copied into the top-level
              target directory. (This is usually *not* what you want.)
            * A directory, such files will be recursively copied into a new
              target subdirectory whose name is such directory's basename.
              (This is usually what you want.)
        """
        toc_datas = []

        for src_root_path_or_glob, trg_root_dir in getattr(hook, 'datas', []):
            # List of the absolute paths of all source paths matching the
            # current glob.
            src_root_paths = glob.glob(src_root_path_or_glob)

            if not src_root_paths:
                raise FileNotFoundError(
                    'Path or glob "%s" not found or matches no files.' % (
                    src_root_path_or_glob))

            for src_root_path in src_root_paths:
                if os.path.isfile(src_root_path):
                    toc_datas.append((
                        os.path.join(
                            trg_root_dir, os.path.basename(src_root_path)),
                        src_root_path, 'DATA'))
                elif os.path.isdir(src_root_path):
                    # If no top-level target directory was passed, default this
                    # to the basename of the top-level source directory.
                    if not trg_root_dir:
                        trg_root_dir = os.path.basename(src_root_path)

                    for src_dir, src_subdir_basenames, src_file_basenames in \
                        os.walk(src_root_path):
                        # Ensure the current source directory is a subdirectory
                        # of the passed top-level source directory. Since
                        # os.walk() does *NOT* follow symlinks by default, this
                        # should be the case. (But let's make sure.)
                        assert src_dir.startswith(src_root_path)

                        # Relative path of the current target directory,
                        # obtained by:
                        #
                        # * Stripping the top-level source directory from the
                        #   current source directory (e.g., removing "/top" from
                        #   "/top/dir").
                        # * Normalizing the result to remove redundant relative
                        #   paths (e.g., removing "./" from "trg/./file").
                        trg_dir = os.path.normpath(
                            os.path.join(
                                trg_root_dir,
                                os.path.relpath(src_dir, src_root_path)))

                        for src_file_basename in src_file_basenames:
                            src_file = os.path.join(src_dir, src_file_basename)
                            if os.path.isfile(src_file):
                                toc_datas.append((
                                    os.path.join(trg_dir, src_file_basename),
                                    src_file, 'DATA'))

        return toc_datas

    # TODO What are 'check_guts' methods useful for?
    def check_guts(self, last_build):
        if last_build == 0:
            logger.info("Building %s because %s non existent", self.__class__.__name__, self.outnm)
            return True
        for fnm in self.inputs:
            if misc.mtime(fnm) > last_build:
                logger.info("Building because %s changed", fnm)
                return True

        data = Target.get_guts(self, last_build)
        if not data:
            return True
        # TODO What does it mean 'data[-6:]' ?
        # TODO Do this code really get executed?
        scripts, pure, binaries, zipfiles, datas, hiddenimports = data[-6:]
        self.scripts = TOC(scripts)
        self.pure = {'toc': TOC(pure), 'code': {}}
        self.binaries = TOC(binaries)
        self.zipfiles = TOC(zipfiles)
        self.datas = TOC(datas)
        self.hiddenimports = hiddenimports
        return False


    def assemble(self):
        """
        This method is the MAIN method for finding all necessary files to be bundled.
        """
        from .config import CONF
        # TODO Find a better place where to put 'base_library.zip' and when to created it.
        # For Python 3 it is necessary to create file 'base_library.zip'
        # containing core Python modules. In Python 3 some built-in modules
        # are written in pure Python. base_library.zip is a way how to have
        # those modules as "built-in".
        if not is_py2:
            libzip_filename = os.path.join(CONF['workpath'], 'base_library.zip')
            create_py3_base_library(libzip_filename)
            # Bundle base_library.zip as data file.
            # Data format of TOC item:   ('relative_path_in_dist_dir', 'absolute_path_on_disk', 'DATA')
            self.datas.append((os.path.basename(libzip_filename), libzip_filename, 'DATA'))

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
            depmanifest = winmanifest.Manifest(type_="win32", name=CONF['specnm'],
                                               processorArchitecture=winmanifest.processor_architecture(),
                                               version=(1, 0, 0, 0))
            depmanifest.filename = os.path.join(CONF['workpath'],
                                                CONF['specnm'] + ".exe.manifest")

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
        self.graph = PyiModuleGraph(HOMEPATH, sys.path + self.pathex,
                                    implies=get_implies())

        # The first script in the analysis is the main user script. Its node is used as
        # the "caller" node for all others. This gives a connected graph rather than
        # a collection of unrelated trees, one for each of self.inputs.
        # The list of scripts is in self.inputs, each as a normalized pathname.

        # List to hold graph nodes of scripts and runtime hooks in use order.
        priority_scripts = []

        # Assume that if the script does not exist, Modulegraph will raise error.
        # Save the graph nodes of each in sequence.
        for script in self.inputs:
            logger.info("Analyzing %s", script)
            priority_scripts.append(self.graph.run_script(script))

        # Analyze the script's hidden imports (named on the command line)
        for modnm in self.hiddenimports:
            logger.debug('Hidden import: %s' % modnm)
            if self.graph.findNode(modnm) is not None:
                logger.debug('Hidden import %r already found', modnm)
                continue
            logger.info("Analyzing hidden import %r", modnm)
            # ModuleGraph throws Import Error if import not found
            try :
                node = self.graph.import_hook(modnm)
            except :
                logger.error("Hidden import %r not found", modnm)

        # TODO move code for handling hooks into a class or function.
        ### Handle hooks.

        logger.info('Looking for import hooks ...')
        # Implement cache of modules for which there exists a hook. Keep order of added items.
        hooks_mod_cache = collections.OrderedDict()  # key - module name, value - path to hook directory.
        # PyInstaller import hooks.
        hooks_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hooks')
        hooks_file_list = glob.glob(os.path.join(hooks_dir, 'hook-*.py'))
        for f in hooks_file_list:
            hooks_mod_cache[os.path.basename(f)[5:-3]] = f
        # Custom import hooks.
        if self.hookspath:
            # Hooks path is a list and we need to cache files from multiple directories.
            for pth in self.hookspath:
                file_list = glob.glob(os.path.join(pth, 'hook-*.py'))
                for f in file_list:
                    name = os.path.basename(f)[5:-3]
                    hooks_mod_cache[name] = pth

        # TODO "temp_toc" appears to be unused and have no side effects.
        # Remove, please.

        # Now find regular hooks and execute them. Get a new TOC, in part
        # because graphing a runtime hook might have added some names, but
        # also because regular hooks can apply to extensions and builtins.
        temp_toc = self.graph.make_a_TOC(['PYMODULE', 'PYSOURCE', 'BUILTIN', 'EXTENSION'])
        module_types = set(['Module', 'SourceModule', 'CompiledModule', 'Package',
                            'Extension', 'Script', 'BuiltinModule'])

        # TODO simplify this loop - functions, etc.
        ### Iterate over import hooks and update ModuleGraph as needed.
        #
        # 1. Iterate in infinite 'while' loop.
        # 2. Apply all possible hooks in one 'while' iteration.
        # 3. Remove applied hooks from the cache.
        # 4. The infinite 'while' loop ends when:
        #    a. hooks cache is empty
        #    b. no new hook was applied in the 'while' iteration.
        #
        while True:
            applied_hooks = []  # Empty means no hook was applied.

            # Iterate over hooks in cache.
            for imported_name, hook_file_name in hooks_mod_cache.items():

                # Skip hook if no module for it is in the graph or the node is not
                # the right type.
                from_node = self.graph.findNode(imported_name)
                node_type = type(from_node).__name__
                if from_node is None:
                    continue
                elif node_type not in module_types:
                    continue

                logger.info('Processing hook   %s' % os.path.basename(hook_file_name))

                # Import hook module from a file.
                # hook_name_space represents the code of 'hook-imported_name.py'
                hook_name_space = importlib_load_source('pyi_hook.'+imported_name, hook_file_name)

                ### Processing hook API.

                # Function hook_name_space.hook(mod) has to be called first because this function
                # could update other attributes - datas, hiddenimports, etc.
                # TODO use directly Modulegraph machinery in the 'def hook(mod)' function.
                if hasattr(hook_name_space, 'hook'):
                    # Process a hook(mod) function. Create a Module object as its API.
                    # TODO: it won't be called "FakeModule" later on
                    mod = FakeModule(imported_name, self.graph)
                    mod = hook_name_space.hook(mod)
                    for item in mod._added_imports:
                        # as with hidden imports, add to graph as called by imported_name
                        self.graph.run_script(item, from_node)
                    for item in mod._added_binaries:
                        assert(item[2] == 'BINARY')
                        self.binaries.append(item)  # Supposed to be TOC form (n,p,'BINARY')
                    for item in mod.datas:
                        assert(item[2] == 'DATA')
                        self.datas.append(item)  # Supposed to be TOC form (n,p,'DATA')
                    for item in mod._deleted_imports:
                        # Remove the graph link between the hooked module and item.
                        # This removes the 'item' node from the graph if no other
                        # links go to it (no other modules import it)
                        self.graph.removeReference(mod.node, item)
                    # TODO: process mod.datas if not empty, tkinter data files

                # hook_name_space.hiddenimports is a list of Python module names that PyInstaller
                # is not able detect.
                if hasattr(hook_name_space, 'hiddenimports'):
                    # push hidden imports into the graph, as if imported from name
                    for item in hook_name_space.hiddenimports:
                        try:
                            to_node = self.graph.findNode(item)
                            if to_node is None:
                                self.graph.import_hook(item, from_node)
                        except ImportError:
                            # Print warning if a module from hiddenimport could not be found.
                            # modulegraph raises ImporError when a module is not found.
                            # Import hook with non-existing hiddenimport is probably a stale hook
                            # that was not updated for a long time.
                            logger.warn("Hidden import '%s' not found (probably old hook)" % item)

                # hook_name_space.excludedimports is a list of Python module names that PyInstaller
                # should not detect as dependency of this module name.
                if hasattr(hook_name_space, 'excludedimports'):
                    # Remove references between module nodes, as if they are not imported from 'name'
                    for item in hook_name_space.excludedimports:
                        try:
                            excluded_node = self.graph.findNode(item)
                            if excluded_node is not None:
                                logger.info("Excluding import '%s'" % item)
                                # Remove implicit reference to a module. Also submodules of the hook name
                                # might reference the module. Remove those references too.
                                safe_to_remove = True
                                referers = self.graph.getReferers(excluded_node)
                                for r in referers:
                                    r_type = type(r).__name__
                                    if r_type in module_types:  # Analyze only relevant types.
                                        if r.identifier.startswith(imported_name):
                                            logger.debug('Removing reference %s' % r.identifier)
                                            # Contains prefix of 'imported_name' - remove reference.
                                            self.graph.removeReference(r, excluded_node)
                                        elif not r.identifier.startswith(item):
                                            # Other modules reference the implicit import - DO NOT remove it.
                                            logger.debug('Excluded import %s referenced by module %s' % (item, r.identifier))
                                            safe_to_remove = False
                                # Remove the implicit module from graph in order to not be further analyzed.
                                # If no other modules reference the implicit import the it is safe to remove
                                # that module from the graph.
                                if safe_to_remove:
                                    self.graph.removeNode(excluded_node)
                            else:
                                logger.info("Excluded import '%s' not found" % item)
                        except ImportError:
                            # excludedimport could not be found.
                            # modulegraph raises ImporError when a module is not found.
                            logger.info("Excluded import '%s' not found" % item)

                # hook_name_space.datas is a list of globs of files or
                # directories to bundle as datafiles. For each
                # glob, a destination directory is specified.
                if hasattr(hook_name_space, 'datas'):
                    # Add desired data files to our datas TOC
                    self.datas.extend(self._format_hook_datas(hook_name_space))

                # hook_name_space.binaries is a list of files to bundle as binaries.
                # Binaries are special that PyInstaller will check if they
                # might depend on other dlls (dynamic libraries).
                if hasattr(hook_name_space, 'binaries'):
                    for bundle_name, pth in hook_name_space.binaries:
                        self.binaries.append((bundle_name, pth, 'BINARY'))

                # TODO implement attribute 'hook_name_space.attrs'
                # hook_name_space.attrs is a list of tuples (attr_name, value) where 'attr_name'
                # is name for Python module attribute that should be set/changed.
                # 'value' is the value of that attribute. PyInstaller will modify
                # mod.attr_name and set it to 'value' for the created .exe file.

                # Remove hook from the cache - it was applied and it is no longer necessary to be
                # applied.
                del hooks_mod_cache[imported_name]
                # Append applied hooks to the list 'applied_hooks'.
                # It is a sign that iteration over hooks should continue.
                applied_hooks.append(imported_name)


            ### All hooks from cache were traversed - stop or run again.
            if not applied_hooks:  # Empty list.
                # No new hook was applied - END of hooks processing.
                break
            else:
                # Run again - reset list 'applied_hooks'.
                applied_hooks = []


        # Analyze run-time hooks.
        # Run-time hooks has to be executed before user scripts. Add them
        # to the beginning of 'priority_scripts'.
        priority_scripts = self.graph.analyze_runtime_hooks(self.custom_runtime_hooks) + priority_scripts

        # 'priority_scripts' is now a list of the graph nodes of custom runtime
        # hooks, then regular runtime hooks, then the PyI loader scripts.
        # Further on, we will make sure they end up at the front of self.scripts

        ### Extract the nodes of the graph as TOCs for further processing.

        # Initialize the scripts list with priority scripts in the proper order.
        self.scripts = self.graph.nodes_to_TOC(priority_scripts)
        # Put all other script names into the TOC after them. (The rthooks names
        # will be found again, but TOC.append skips duplicates.)
        #self.scripts = self.graph.make_a_TOC(['PYSOURCE'], self.scripts)

        # Extend the binaries list with all the Extensions modulegraph has found.
        self.binaries  = self.graph.make_a_TOC(['EXTENSION', 'BINARY'],self.binaries)
        # Fill the "pure" list with pure Python modules.
        self.pure['toc'] =  self.graph.make_a_TOC(['PYMODULE'])
        # And get references to module code objects constructed by ModuleGraph
        # to avoid writing .pyc/pyo files to hdd.
        self.pure['code'].update(self.graph.get_code_objects())

        # Add remaining binary dependencies - analyze Python C-extensions and what
        # DLLs they depend on.
        logger.info('Looking for dynamic libraries')
        self.binaries.extend(bindepend.Dependencies(self.binaries, manifest=depmanifest))

        ### TODO implement including Python eggs. Shoudl be the eggs printed to console as INFO msg?
        logger.info('Looking for eggs - TODO')
        # TODO: ImpTracker could flag a module as residing in a zip file (because an
        # egg that had not yet been installed??) and the old code would do this:
        # scripts.insert(-1, ('_pyi_egg_install.py',
        #     os.path.join(_init_code_path, '_pyi_egg_install.py'), 'PYSOURCE'))
        # It appears that Modulegraph will expand an uninstalled egg but need test
        self.zipfiles = TOC()
        # Copied from original code
        if is_win:
            depmanifest.writeprettyxml()

        # Verify that Python dynamic library can be found.
        # Without dynamic Python library PyInstaller cannot continue.
        self._check_python_library(self.binaries)

        # Get the saved details of a prior run, if any. Would not exist if
        # the user erased the work files, or gave a different --workpath
        # or specified --clean.
        try:
            oldstuff = load_py_data_struct(self.out)
        except:
            oldstuff = None

        # Collect the work-product of this run
        newstuff = tuple([getattr(self, g[0]) for g in self.GUTS])
        # If there was no previous, or if it is different, save the new
        if oldstuff != newstuff:
            # Save all the new stuff to avoid regenerating it later, maybe
            save_py_data_struct(self.out, newstuff)
            # Write warnings about missing modules. Get them from the graph
            # and use the graph to figure out who tried to import them.
            # TODO: previously we could say whether an import was top-level,
            # deferred (in a def'd function) or conditional (in an if stmt).
            # That information is not available from ModuleGraph at this time.
            # When that info is available change this code to write one line for
            # each importer-name, with type of import for that importer
            # "no module named foo conditional/deferred/toplevel importy by bar"
            miss_toc = self.graph.make_a_TOC(['MISSING'])
            if len(miss_toc) : # there are some missing modules
                wf = open(CONF['warnfile'], 'w')
                for (n, p, t) in miss_toc :
                    importer_names = self.graph.importer_names(n)
                    wf.write( 'no module named '
                              + n
                              + ' - imported by '
                              + ', '.join(importer_names)
                              + '\n'
                              )
                wf.close()
                logger.info("Warnings written to %s", CONF['warnfile'])
            return 1
        else :
            logger.info("%s no change!", self.out)
            return 0

    def _check_python_library(self, binaries):
        """
        Verify presence of the Python dynamic library in the binary dependencies.
        Python library is an essential piece that has to be always included.
        """
        # First check that libpython is in resolved binary dependencies.
        for (nm, filename, typ) in binaries:
            if typ == 'BINARY' and nm in PYDYLIB_NAMES:
                # Just print its filename and return.
                logger.info('Using Python library %s', filename)
                # Checking was successful - end of function.
                return

        # Python lib not in dependencies - try to find it.
        logger.info('Python library not in binary depedencies. Doing additional searching...')
        python_lib = bindepend.get_python_library_path()
        if python_lib:
            logger.debug('Adding Python library to binary dependencies')
            binaries.append((os.path.basename(python_lib), python_lib, 'BINARY'))
            logger.info('Using Python library %s', python_lib)
        else:
            msg = """Python library not found! This usually happens on Debian/Ubuntu
where you need to install Python library:

  apt-get install python3-dev
  apt-get install python-dev

"""
            raise IOError(msg)



class PYZ(Target):
    """
    Creates a ZlibArchive that contains all pure Python modules.
    """
    typ = 'PYZ'

    def __init__(self, toc_dict, name=None, cipher=None):
        """
        toc_dict
            toc_dict['toc']
                A TOC (Table of Contents), normally an Analysis.pure['toc']?
            toc_dict['code']
                A dict of module code objects from ModuleGraph.
        name
                A filename for the .pyz. Normally not needed, as the generated
                name will do fine.
        cipher
                The block cipher that will be used to encrypt Python bytecode.
        """
        from .config import CONF
        Target.__init__(self)
        self.toc = toc_dict['toc']
        # Use code objects directly from ModuleGraph to speed up PyInstaller.
        self.code_dict = toc_dict['code']
        self.name = name
        if name is None:
            self.name = self.out[:-3] + 'pyz'
        # Compile top-level modules so we could run them at app startup.
        self.dependencies = misc.compile_py_files(get_bootstrap_modules(), CONF['workpath'])
        self.cipher = cipher
        self.__postinit__()

    GUTS = (('name', _check_guts_eq),
            ('level', _check_guts_eq),
            ('toc', _check_guts_toc),  # todo: pyc=1
            )

    def check_guts(self, last_build):
        if not os.path.exists(self.name):
            logger.info("Rebuilding %s because %s is missing",
                        self.outnm, os.path.basename(self.name))
            return True

        data = Target.get_guts(self, last_build)
        if not data:
            return True
        return False

    def assemble(self):
        logger.info("Building PYZ (ZlibArchive) %s", os.path.basename(self.out))
        pyz = pyi_archive.ZlibArchive(code_dict=self.code_dict, cipher=self.cipher)
        # Do not bundle PyInstaller bootstrap modules into PYZ archive.
        toc = self.toc - self.dependencies
        pyz.build(self.name, toc)
        # FIXME compression level was dropped - remove it from the save_py_data_struct
        compresssion_level = 0
        save_py_data_struct(self.out, (self.name, compresssion_level, self.toc))
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
    from .config import CONF
    # On darwin a cache is required anyway to keep the libaries
    # with relative install names. Caching on darwin does not work
    # since we need to modify binary headers to use relative paths
    # to dll depencies and starting with '@loader_path'.
    if not strip and not upx and not is_darwin and not is_win:
        return fnm

    if dist_nm is not None and ":" in dist_nm:
        # A file embedded in another pyinstaller build via multipackage
        # No actual file exists to process
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
    arch = platform.architecture()[0]
    cachedir = os.path.join(CONFIGDIR, 'bincache%d%d_%s_%s' % (strip, upx, pyver, arch))
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)
    cacheindexfn = os.path.join(cachedir, "index.dat")
    if os.path.exists(cacheindexfn):
        cache_index = load_py_data_struct(cacheindexfn)
    else:
        cache_index = {}

    # Verify if the file we're looking for is present in the cache.
    # Use the dist_mn if given to avoid different extension modules
    # sharing the same basename get corrupted.
    if dist_nm:
        basenm = os.path.normcase(dist_nm)
    else:
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

    # Change manifest and its deps to private assemblies
    if fnm.lower().endswith(".manifest"):
        manifest = winmanifest.Manifest()
        manifest.filename = fnm
        with open(fnm, "rb") as f:
            manifest.parse_string(f.read())
        if manifest.publicKeyToken:
            logger.info("Changing %s into private assembly", os.path.basename(fnm))
        manifest.publicKeyToken = None
        for dep in manifest.dependentAssemblies:
            # Exclude common-controls which is not bundled
            if dep.name != "Microsoft.Windows.Common-Controls":
                dep.publicKeyToken = None

        manifest.writeprettyxml(cachedfile)
        return cachedfile

    if upx:
        if strip:
            fnm = checkCache(fnm, strip=True, upx=False)
        bestopt = "--best"
        # FIXME: Linux builds of UPX do not seem to contain LZMA (they assert out)
        # A better configure-time check is due.
        if CONF["hasUPX"] >= (3,) and os.name == "nt":
            bestopt = "--lzma"

        upx_executable = "upx"
        if CONF.get('upx_dir'):
            upx_executable = os.path.join(CONF['upx_dir'], upx_executable)
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

    if not os.path.exists(os.path.dirname(cachedfile)):
        os.makedirs(os.path.dirname(cachedfile))
    shutil.copy2(fnm, cachedfile)
    os.chmod(cachedfile, 0o755)

    if os.path.splitext(fnm.lower())[1] in (".pyd", ".dll"):
        # When shared assemblies are bundled into the app, they must be
        # transformed into private assemblies or else the assembly
        # loader will not search for them in the app folder. To support
        # this, all manifests in the app must be modified to point to
        # the private assembly.

        # Also, if python.exe has dependent assemblies, check for
        # embedded manifest of cached pyd file because we may need to
        # 'fix it' for pyinstaller
        try:
            res = winmanifest.GetManifestResources(os.path.abspath(cachedfile))
        except winresource.pywintypes.error as e:
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
                        except Exception as exc:
                            logger.error("Cannot parse manifest resource %s, "
                                         "%s from", name, language)
                            logger.error(cachedfile)
                            logger.exception(exc)
                        else:
                            # change manifest to private assembly
                            if manifest.publicKeyToken:
                                logger.info("Changing %s into a private assembly",
                                            os.path.basename(fnm))
                            manifest.publicKeyToken = None

                            # Fix the embedded manifest (if any):
                            # Extension modules built with Python 2.6.5 have
                            # an empty <dependency> element, we need to add
                            # dependentAssemblies from python.exe for
                            # pyinstaller.
                            _depNames = set([dep.name for dep in
                                             manifest.dependentAssemblies])
                            for pydep in CONF['pylib_assemblies']:
                                if not pydep.name in _depNames:
                                    logger.info("Adding %r to dependent "
                                                "assemblies of %r",
                                                pydep.name, cachedfile)
                                    manifest.dependentAssemblies.append(pydep)
                                    _depNames.update(pydep.name)

                            # Change dep to private assembly
                            for dep in manifest.dependentAssemblies:
                                # Exclude common-controls which is not bundled
                                if dep.name != "Microsoft.Windows.Common-Controls":
                                    dep.publicKeyToken = None
                            try:
                                manifest.update_resources(os.path.abspath(cachedfile),
                                                          [name],
                                                          [language])
                            except Exception as e:
                                logger.error(os.path.abspath(cachedfile))
                                raise

    if cmd:
        try:
            logger.info("Executing - " + ' '.join(cmd))
            compat.exec_command(*cmd)
        except OSError as e:
            raise SystemExit("Execution failed: %s" % e)

    # update cache index
    cache_index[basenm] = digest
    save_py_data_struct(cacheindexfn, cache_index)

    # On Mac OS X we need relative paths to dll dependencies
    # starting with @executable_path
    if is_darwin:
        dylib.mac_set_relative_dylib_deps(cachedfile, dist_nm)
    return cachedfile


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
            logger.info("Rebuilding %s because %s is missing",
                        self.outnm, os.path.basename(self.name))
            return 1

        data = Target.get_guts(self, last_build)
        if not data:
            return True
        # todo: toc equal
        return False

    def assemble(self):
        logger.info("Building PKG (CArchive) %s", os.path.basename(self.name))
        trash = []
        mytoc = []
        seenInms = {}
        seenFnms = {}
        toc = self.toc
        # 'inm'  - relative filename inside a CArchive
        # 'fnm'  - absolute filename as it is on the file system.
        for inm, fnm, typ in toc:
            # Ensure filename 'fnm' is not None or empty string. Otherwise
            # it will fail in case of 'typ' being type OPTION.
            if fnm and not os.path.isfile(fnm) and is_path_to_egg(fnm):
                # file is contained within python egg, it is added with the egg
                continue
            if typ in ('BINARY', 'EXTENSION', 'DEPENDENCY'):
                if self.exclude_binaries and typ != 'DEPENDENCY':
                    self.dependencies.append((inm, fnm, typ))
                else:
                    if typ == 'BINARY':
                        # Avoid importing the same binary extension twice. This might
                        # happen if they come from different sources (eg. once from
                        # binary dependence, and once from direct import).
                        if inm in seenInms:
                            logger.warn("Two binaries added with the same internal "
                                        "name. %s was placed at %s previously. "
                                        "Skipping %s." %
                                        (seenInms[inm], inm, fnm))
                            continue

                        # Warn if the same binary extension was included
                        # with multiple internal names
                        if fnm in seenFnms:
                            logger.warn("One binary added with two internal "
                                        "names. %s was placed at %s previously." %
                                        (fnm, seenFnms[fnm]))
                    seenInms[inm] = fnm
                    seenFnms[fnm] = inm

                    fnm = checkCache(fnm, strip=self.strip_binaries,
                                     upx=(self.upx_binaries and (is_win or is_cygwin)),
                                     dist_nm=inm)

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
        save_py_data_struct(self.out,
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
            uac_admin
                Windows only. Setting to True creates a Manifest with will request
                elevation upon application restart
            uac_uiaccess
                Windows only. Setting to True allows an elevated application to
                work with Remote Desktop
        """
        from .config import CONF
        Target.__init__(self)

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
        # If ``append_pkg`` is false, the archive will not be appended
        # to the exe, but copied beside it.
        self.append_pkg = kwargs.get('append_pkg', True)

        # On Windows allows the exe to request admin privileges.
        self.uac_admin = kwargs.get('uac_admin', False)
        self.uac_uiaccess = kwargs.get('uac_uiaccess', False)

        if CONF['hasUPX']:
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
            self.name = os.path.join(CONF['workpath'], os.path.basename(self.name))
        else:
            # onefile mode - create executable in DISTPATH.
            self.name = os.path.join(CONF['distpath'], os.path.basename(self.name))

        # Base name of the EXE file without .exe suffix.
        base_name = os.path.basename(self.name)
        if is_win or is_cygwin:
            base_name = os.path.splitext(base_name)[0]
        self.pkgname = base_name + '.pkg'

        self.toc = TOC()

        ### Pass option -S to Python interpreter to disable the 'site' module.
        # With this option PyInstaller  won't append user-specific sitedirs to
        # sys.path.
        args += ([('S', None, 'OPTION')],)

        for arg in args:
            if isinstance(arg, TOC):
                self.toc.extend(arg)
            elif isinstance(arg, Target):
                self.toc.append((os.path.basename(arg.name), arg.name, arg.typ))
                self.toc.extend(arg.dependencies)
            else:
                self.toc.extend(arg)

        if is_win:
            filename = os.path.join(CONF['workpath'], CONF['specnm'] + ".exe.manifest")
            self.manifest = winmanifest.create_manifest(filename, self.manifest,
                self.console, self.uac_admin, self.uac_uiaccess)
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
            logger.info("Rebuilding %s because %s missing",
                        self.outnm, os.path.basename(self.name))
            return 1
        if not self.append_pkg and not os.path.exists(self.pkgname):
            logger.info("Rebuilding because %s missing",
                        os.path.basename(self.pkgname))
            return 1

        data = Target.get_guts(self, last_build)
        if not data:
            return True

        icon, versrsrc, resources = data[3:6]
        if (versrsrc or resources) and not is_win:
            # todo: really ignore :-)
            logger.warn('ignoring version, manifest and resources, platform not capable')
        if icon and not (is_win or is_darwin):
            logger.warn('ignoring icon, platform not capable')

        mtm = data[-1]
        if mtm != misc.mtime(self.name):
            logger.info("Rebuilding %s because mtimes don't match", self.outnm)
            return True
        if mtm < misc.mtime(self.pkg.out):
            logger.info("Rebuilding %s because pkg is more recent", self.outnm)
            return True

        return False

    def _bootloader_file(self, exe):
        """
        Pick up the right bootloader file - debug, console, windowed.
        """
        # Having console/windowed bootolader makes sense only on Windows and
        # Mac OS X.
        if is_win or is_darwin:
            if not self.console:
                exe = exe + 'w'
        # There are two types of bootloaders:
        # run     - release, no verbose messages in console.
        # run_d   - contains verbose messages in console.
        if self.debug:
            exe = exe + '_d'
        bootloader_file = os.path.join(HOMEPATH, 'PyInstaller', 'bootloader', PLATFORM, exe)
        logger.info('Bootloader %s' % bootloader_file)
        return bootloader_file

    def assemble(self):
        logger.info("Building EXE from %s", os.path.basename(self.out))
        trash = []
        if not os.path.exists(os.path.dirname(self.name)):
            os.makedirs(os.path.dirname(self.name))
        outf = open(self.name, 'wb')
        exe = self._bootloader_file('run')
        if is_win or is_cygwin:
            exe = exe + '.exe'

        if not os.path.exists(exe):
            raise SystemExit(_MISSING_BOOTLOADER_ERRORMSG)

        if is_win and not self.exclude_binaries:
            # Windows and onefile mode - embed manifest into exe.
            logger.info('Onefile Mode - Embedding Manifest into EXE file')
            tmpnm = tempfile.mktemp()
            shutil.copy2(exe, tmpnm)
            os.chmod(tmpnm, 0o755)

            # In onefile mode, dependencies in the onefile manifest
            # refer to files that are about to be unpacked when the exe
            # is run. The Windows DLL loader doesn't know that and
            # refuses to run the exe at all. Since the .exe does not in
            # fact depend on those, and the actual manifest will be used
            # later when an activation context is created, all
            # dependencies are removed from the embedded manifest. 
            self.manifest.dependentAssemblies = []
            self.manifest.update_resources(tmpnm, [1]) # 1 for executable
            trash.append(tmpnm)
            exe = tmpnm

        if is_win and (self.icon or self.versrsrc or self.resources):
            tmpnm = tempfile.mktemp()
            shutil.copy2(exe, tmpnm)
            os.chmod(tmpnm, 0o755)
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
                except winresource.pywintypes.error as exc:
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
                    except winresource.pywintypes.error as exc:
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

        if is_darwin:
            # Fix Mach-O header for codesigning on OS X.
            logger.info("Fixing EXE for code signing %s", self.name)
            from PyInstaller.utils import osxutils
            osxutils.fix_exe_for_code_signing(self.name)
            pass

        os.chmod(self.name, 0o755)
        guts = (self.name, self.console, self.debug, self.icon,
                self.versrsrc, self.resources, self.strip, self.upx,
                misc.mtime(self.name))
        assert len(guts) == len(self.GUTS)
        save_py_data_struct(self.out, guts)
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
        logger.info("Building DLL %s", os.path.basename(self.out))
        outf = open(self.name, 'wb')
        dll = self._bootloader_file('inprocsrvr') + '.dll'
        if not os.path.exists(dll):
            raise SystemExit(_MISSING_BOOTLOADER_ERRORMSG)
        self.copy(dll, outf)
        self.copy(self.pkg.name, outf)
        outf.close()
        os.chmod(self.name, 0o755)
        save_py_data_struct(self.out,
                   (self.name, self.console, self.debug, self.icon,
                    self.versrsrc, self.manifest, self.resources, self.strip, self.upx, misc.mtime(self.name)))
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
        from .config import CONF
        Target.__init__(self)
        self.strip_binaries = kws.get('strip', False)

        if CONF['hasUPX']:
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
        self.name = os.path.join(CONF['distpath'], os.path.basename(self.name))

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
        logger.info("Building COLLECT %s", os.path.basename(self.out))
        os.makedirs(self.name)
        toc = add_suffix_to_extensions(self.toc)
        for inm, fnm, typ in toc:
            if not os.path.exists(fnm) or not os.path.isfile(fnm) and is_path_to_egg(fnm):
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
                os.chmod(tofnm, 0o755)
        save_py_data_struct(self.out,
                 (self.name, self.strip_binaries, self.upx_binaries, self.toc))
        return 1


class BUNDLE(Target):
    def __init__(self, *args, **kws):
        from .config import CONF

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
        self.name = os.path.join(CONF['distpath'], base_name)

        self.appname = os.path.splitext(base_name)[0]
        self.version = kws.get("version", "0.0.0")
        self.toc = TOC()
        self.strip = False
        self.upx = False

        # .app bundle identifier for Code Signing
        self.bundle_identifier = kws.get('bundle_identifier')
        if not self.bundle_identifier:
            # Fallback to appname.
            self.bundle_identifier = self.appname

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
                    self.name = os.path.join(CONF['specpath'], self.appname + ".app")
                else:
                    self.name = os.path.join(CONF['specpath'], self.name)
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
        logger.info("Building BUNDLE %s", os.path.basename(self.out))

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

                           # Required by 'codesign' utility.
                           # The value for CFBundleIdentifier is used as the default unique
                           # name of your program for Code Signing purposes.
                           # It even identifies the APP for access to restricted OS X areas
                           # like Keychain.
                           #
                           # The identifier used for signing must be globally unique. The usal
                           # form for this identifier is a hierarchical name in reverse DNS
                           # notation, starting with the toplevel domain, followed by the
                           # company name, followed by the department within the company, and
                           # ending with the product name. Usually in the form:
                           #   com.mycompany.department.appname
                           # Cli option --osx-bundle-identifier sets this value.
                           "CFBundleIdentifier": self.bundle_identifier,

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
                           "LSBackgroundOnly": "0",

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

        toc = add_suffix_to_extensions(self.toc)
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

        logger.info('moving BUNDLE data files to Resource directory')

        ## For some hooks move resource to ./Contents/Resources dir.
        # PyQt4/PyQt5 hooks: On Mac Qt requires resources 'qt_menu.nib'.
        # It is moved from MacOS directory to Resources.
        qt_menu_dir = os.path.join(self.name, 'Contents', 'MacOS', 'qt_menu.nib')
        qt_menu_dest = os.path.join(self.name, 'Contents', 'Resources', 'qt_menu.nib')
        if os.path.exists(qt_menu_dir):
            shutil.move(qt_menu_dir, qt_menu_dest)

        # Mac OS X Code Signing does not work when .app bundle contains
        # data files in dir ./Contents/MacOS.
        #
        # Move all directories from ./MacOS/ to ./Resources and create symlinks
        # in ./MacOS.
        bin_dir =os.path.join(self.name, 'Contents', 'MacOS')
        res_dir =os.path.join(self.name, 'Contents', 'Resources')
        # Qt plugin directories does not contain data files.
        ignore_dirs = set(['qt4_plugins', 'qt5_plugins'])
        dirs = os.listdir(bin_dir)
        for d in dirs:
            abs_d = os.path.join(bin_dir, d)
            res_d = os.path.join(res_dir, d)
            if os.path.isdir(abs_d) and d not in ignore_dirs:
                shutil.move(abs_d, res_d)
                os.symlink(os.path.relpath(res_d, os.path.dirname(abs_d)), abs_d)

        return 1


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
            if misc.mtime(d) > last_build:
                logger.info("Building %s because directory %s changed",
                            self.outnm, d)
                return True
            for nm in os.listdir(d):
                path = os.path.join(d, nm)
                if os.path.isdir(path):
                    stack.append(path)
        self.data = toc
        return False

    def assemble(self):
        logger.info("Building Tree %s", os.path.basename(self.out))
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
            oldstuff = load_py_data_struct(self.out)
        except:
            oldstuff = None
        newstuff = (self.root, self.prefix, self.excludes, self.data)
        if oldstuff != newstuff:
            save_py_data_struct(self.out, newstuff)
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
        Synchronize the Analysis result with the needed dependencies.
        """
        for toc in (analysis.binaries, analysis.datas):
            for i, tpl in enumerate(toc):
                if not tpl[1] in self._dependencies:
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
    # TODO use os.path.relpath instead
    def _get_relative_path(self, startpath, topath):
        start = startpath.split(os.sep)[:-1]
        start = ['..'] * len(start)
        if start:
            start.append(topath)
            return os.sep.join(start)
        else:
            return topath


class ExecutableBuilder(object):
    """
    Class that constructs the executable.
    """
    # TODO wrap the 'main' and 'build' function into this class.


def build(spec, distpath, workpath, clean_build):
    """
    Build the executable according to the created SPEC file.
    """
    from .config import CONF

    # Ensure starting tilde and environment variables get expanded in distpath / workpath.
    # '~/path/abc', '${env_var_name}/path/abc/def'
    distpath = compat.expand_path(distpath)
    workpath = compat.expand_path(workpath)
    CONF['spec'] = compat.expand_path(spec)

    CONF['specpath'], CONF['specnm'] = os.path.split(spec)
    CONF['specnm'] = os.path.splitext(CONF['specnm'])[0]

    # Add 'specname' to workpath and distpath if they point to PyInstaller homepath.
    if os.path.dirname(distpath) == HOMEPATH:
        distpath = os.path.join(HOMEPATH, CONF['specnm'], os.path.basename(distpath))
    CONF['distpath'] = distpath
    if os.path.dirname(workpath) == HOMEPATH:
        workpath = os.path.join(HOMEPATH, CONF['specnm'], os.path.basename(workpath), CONF['specnm'])
    else:
        workpath = os.path.join(workpath, CONF['specnm'])

    CONF['warnfile'] = os.path.join(workpath, 'warn%s.txt' % CONF['specnm'])

    # Clean PyInstaller cache (CONFIGDIR) and temporary files (workpath)
    # to be able start a clean build.
    if clean_build:
        logger.info('Removing temporary files and cleaning cache in %s', CONFIGDIR)
        for pth in (CONFIGDIR, workpath):
            if os.path.exists(pth):
                # Remove all files in 'pth'.
                for f in glob.glob(pth + '/*'):
                    # Remove dirs recursively.
                    if os.path.isdir(f):
                        shutil.rmtree(f)
                    else:
                        os.remove(f)

    # Create DISTPATH and workpath if they does not exist.
    for pth in (CONF['distpath'], workpath):
        if not os.path.exists(pth):
            os.makedirs(pth)

    # Construct NAMESPACE for running the Python code from .SPEC file.
    # NOTE: Passing NAMESPACE allows to avoid having global variables in this
    #       module and makes isolated environment for running tests.
    # NOTE: Defining NAMESPACE allows to map any class to a apecific name for .SPEC.
    # FIXME: Some symbols might be missing. Add them if there are some failures.
    # TODO: What from this .spec API is deprecated and could be removed?
    spec_namespace = {
        # Set of global variables that can be used while processing .spec file.
        # Some of them act as configuration options.
        'DISTPATH': CONF['distpath'],
        'HOMEPATH': HOMEPATH,
        'SPEC': CONF['spec'],
        'specnm': CONF['specnm'],
        'SPECPATH': CONF['specpath'],
        'WARNFILE': CONF['warnfile'],
        'workpath': workpath,
        # PyInstaller classes for .spec.
        'Analysis': Analysis,
        'BUNDLE': BUNDLE,
        'COLLECT': COLLECT,
        'DLL': DLL,
        'EXE': EXE,
        'MERGE': MERGE,
        'PYZ': PYZ,
        'Tree': Tree,
        # Old classes for .spec - raise Exception for user.
        'TkPKG': lambda *args, **kwargs: _old_api_error('TkPKG'),
        'TkTree': lambda *args, **kwargs: _old_api_error('TkTree'),
        # Python modules available for .spec.
        'os': os,
    }

    # Set up module PyInstaller.config for passing some arguments to 'exec'
    # function.
    from .config import CONF
    CONF['workpath'] = workpath

    # Executing the specfile.
    with open(spec, 'r') as f:
        text = f.read()
    exec(text, spec_namespace)


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

    from .config import CONF
    CONF['noconfirm'] = noconfirm

    # Some modules are included if they are detected at build-time or
    # if a command-line argument is specified. (e.g. --ascii)
    if CONF.get('hiddenimports') is None:
        CONF['hiddenimports'] = []
    # Test unicode support.
    if not ascii:
        CONF['hiddenimports'].extend(misc.get_unicode_modules())

    # FIXME: this should be a global import, but can't due to recursive imports
    # If configuration dict is supplied - skip configuration step.
    if pyi_config is None:
        import PyInstaller.configure as configure
        CONF.update(configure.get_config(kw.get('upx_dir')))
    else:
        CONF.update(pyi_config)

    # Append assemblies to dependencies only on Winodws.
    if is_win:
        CONF['pylib_assemblies'] = bindepend.getAssemblies(sys.executable)

    if CONF['hasUPX']:
        setupUPXFlags()

    CONF['ui_admin'] = kw.get('ui_admin', False)
    CONF['ui_access'] = kw.get('ui_uiaccess', False)

    build(specfile, kw.get('distpath'), kw.get('workpath'), kw.get('clean_build'))
