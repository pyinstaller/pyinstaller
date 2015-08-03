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
import os
import shutil
import sys


# Relative imports to PyInstaller modules.
from PyInstaller import HOMEPATH, DEFAULT_DISTPATH, DEFAULT_WORKPATH
from PyInstaller import compat
from PyInstaller import log as logging
from PyInstaller.building.utils import _check_guts_toc_mtime
from PyInstaller.utils.misc import absnormpath
from PyInstaller.compat import is_py2, is_win, PYDYLIB_NAMES
from PyInstaller.compat import importlib_load_source
from PyInstaller.depend import bindepend
from PyInstaller.depend.analysis import PyiModuleGraph, FakeModule
from PyInstaller.building.api import PYZ, EXE, DLL, COLLECT, MERGE
from PyInstaller.building.osx import BUNDLE
from PyInstaller.building.datastruct import TOC, Target, Tree, _check_guts_eq
from PyInstaller.depend.utils import create_py3_base_library
from PyInstaller.archive import pyz_crypto
from PyInstaller.utils import misc
from PyInstaller.utils.misc import save_py_data_struct, load_py_data_struct
from PyInstaller.lib.modulegraph.find_modules import get_implies
from ..configure import get_importhooks_dir

if is_win:
    from PyInstaller.utils.win32 import winmanifest

logger = logging.getLogger(__name__)

STRINGTYPE = type('')
TUPLETYPE = type((None,))

rthooks = {}

# place where the loader modules and initialization scripts live
_init_code_path = os.path.join(HOMEPATH, 'PyInstaller', 'loader')


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
        from ..config import CONF

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
            pyi_crypto_key_path = os.path.join(CONF['workpath'], 'pyimod00_crypto_key.py')
            with open(pyi_crypto_key_path, 'w') as f:
                f.write('key = %r\n' % cipher.key)
            logger.info('Adding dependencies on pyi_crypto.py module')
            self.hiddenimports.append(pyz_crypto.get_crypto_hiddenimports())

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
        from ..config import CONF


        # Instantiate a ModuleGraph. The class is defined at end of this module.
        # The argument is the set of paths to use for imports: sys.path,
        # plus our loader, plus other paths from e.g. --path option).
        module_paths = self.pathex + sys.path
        self.graph = PyiModuleGraph(HOMEPATH, path=module_paths,
                                    implies=get_implies())


        # TODO Find a better place where to put 'base_library.zip' and when to created it.
        # For Python 3 it is necessary to create file 'base_library.zip'
        # containing core Python modules. In Python 3 some built-in modules
        # are written in pure Python. base_library.zip is a way how to have
        # those modules as "built-in".
        if not is_py2:
            libzip_filename = os.path.join(CONF['workpath'], 'base_library.zip')
            create_py3_base_library(libzip_filename, graph=self.graph)
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
        # Implement cache of modules for which there exists a hook.
        hooks_mod_cache = {}  # key - module name, value - path to hook directory.
        # PyInstaller import hooks.
        hooks_pathes = [get_importhooks_dir()]
        if self.hookspath:
            # Custom import hooks
            hooks_pathes.extend(self.hookspath)
        for pth in hooks_pathes:
            hooks_file_list = glob.glob(os.path.join(pth, 'hook-*.py'))
            for f in hooks_file_list:
                name = os.path.basename(f)[5:-3]
                hooks_mod_cache[name] = os.path.abspath(f)

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
        module_types = set(['Module', 'SourceModule', 'CompiledModule', 'Package',
                            'Extension', 'Script', 'BuiltinModule'])
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

                # Append applied hooks to the list 'applied_hooks'.
                # These will be removed after the inner loop finishs.
                # It also is a marker that iteration over hooks should
                # continue.
                applied_hooks.append(imported_name)


            ### All hooks from cache were traversed - stop or run again.
            if not applied_hooks:  # Empty list.
                # No new hook was applied - END of hooks processing.
                break
            else:
                # Remove applied hooks from the cache - its not
                # necessary apply then again.
                for imported_name in applied_hooks:
                    del hooks_mod_cache[imported_name]
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


class ExecutableBuilder(object):
    """
    Class that constructs the executable.
    """
    # TODO wrap the 'main' and 'build' function into this class.


def build(spec, distpath, workpath, clean_build):
    """
    Build the executable according to the created SPEC file.
    """
    from ..config import CONF

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

    # Clean PyInstaller cache (CONF['configdir']) and temporary files (workpath)
    # to be able start a clean build.
    if clean_build:
        logger.info('Removing temporary files and cleaning cache in %s', CONF['configdir'])
        for pth in (CONF['configdir'], workpath):
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
        'TOC': TOC,
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
        'pyi_crypto': pyz_crypto,
    }

    # Set up module PyInstaller.config for passing some arguments to 'exec'
    # function.
    from ..config import CONF
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

    from ..config import CONF
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
