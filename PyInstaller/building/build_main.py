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
from PyInstaller.depend import bindepend
from PyInstaller.depend.analysis import initialize_modgraph
from PyInstaller.building.api import PYZ, EXE, DLL, COLLECT, MERGE
from PyInstaller.building.osx import BUNDLE
from PyInstaller.building.datastruct import TOC, Target, Tree, _check_guts_eq
from PyInstaller.depend.utils import create_py3_base_library
from PyInstaller.archive import pyz_crypto
from PyInstaller.utils import misc
from ..configure import get_importhooks_dir
from .imphook import HooksCache, ImportHook

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
        self.pure = TOC()
        self.binaries = TOC()
        self.zipfiles = TOC()
        self.datas = TOC()
        self.dependencies = TOC()
        self.__postinit__()

    _GUTS = (# input parameters
            ('inputs', _check_guts_eq),  # parameter `scripts`
            ('pathex', _check_guts_eq),
            ('hiddenimports', _check_guts_eq),
            ('hookspath', _check_guts_eq),
            ('excludes', _check_guts_eq),
            ('custom_runtime_hooks', _check_guts_eq),
            #'cipher': no need to check as it is implied by an
            # additional hidden import

            #calculated/analysed values
            ('scripts', _check_guts_toc_mtime),
            ('pure', lambda *args: _check_guts_toc_mtime(*args, **{'pyc': 1})),
            ('binaries', _check_guts_toc_mtime),
            ('zipfiles', _check_guts_toc_mtime),
            ('datas', _check_guts_toc_mtime),
            # TODO: Need to add "dependencies"?
            )

    def _check_guts(self, data, last_build):
        if Target._check_guts(self, data, last_build):
            return True
        for fnm in self.inputs:
            if misc.mtime(fnm) > last_build:
                logger.info("Building because %s changed", fnm)
                return True
        # Now we know that none of the input parameters and none of
        # the input files has changed. So take the values calculated
        # resp. analysed in the last run and store them in `self`.
        self.scripts = TOC(data['scripts'])
        self.pure = TOC(data['pure'])
        self.binaries = TOC(data['binaries'])
        self.zipfiles = TOC(data['zipfiles'])
        self.datas = TOC(data['datas'])
        return False

    def assemble(self):
        """
        This method is the MAIN method for finding all necessary files to be bundled.
        """
        from ..config import CONF

        # Either instantiate a ModuleGraph object or for tests reuse
        # dependency graph already created.
        if 'tests_modgraph' in CONF:
            logger.info('Reusing basic module graph object.')
            self.graph = CONF['tests_modgraph']
        else:
            self.graph = initialize_modgraph()

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

        # Expand sys.path of module graph.
        # The attribute is the set of paths to use for imports: sys.path,
        # plus our loader, plus other paths from e.g. --path option).
        self.graph.path = self.pathex + self.graph.path


        logger.info("running Analysis %s", self.tocbasename)
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


        ### Handle hooks.
        #
        # Iterate over import hooks and update ModuleGraph as needed.
        #
        # 1. Iterate in infinite 'while' loop.
        # 2. Apply all possible hooks in one 'while' iteration.
        # 3. Remove applied hooks from the cache.
        # 4. The infinite 'while' loop ends when:
        #    a. hooks cache is empty
        #    b. no new hook was applied in the 'while' iteration.
        #
        logger.info('Looking for import hooks ...')
        module_types = set(['Module', 'SourceModule', 'CompiledModule', 'Package',
                            'Extension', 'Script', 'BuiltinModule'])
        hooks_cache = HooksCache(get_importhooks_dir())
        # Custom import hooks
        if self.hookspath:
            hooks_cache.add_custom_paths(self.hookspath)

        while True:
            # This ensures that import hooks get applied only once.
            applied_hooks = []  # Empty means no hook was applied.

            # Iterate over hooks in cache.
            for imported_name in hooks_cache:

                # Skip hook if no module for it is in the graph or the node is not
                # the right type.
                from_node = self.graph.findNode(imported_name)
                node_type = type(from_node).__name__
                if from_node is None:
                    continue
                elif node_type not in module_types:
                    continue

                # Import hook module from a file.
                imphook_object = ImportHook(imported_name, hooks_cache[imported_name])
                # Expad module dependency graph.
                imphook_object.update_dependencies(self.graph)
                # Update self.binaries and self.datas by files found in import hook.
                # TODO do this at once all hooks after they are applied and only for those modules that are reachable from top-level script.
                for a, b in imphook_object.binaries:
                    self.binaries.append((a, b, 'BINARY'))
                for a, b in imphook_object.datas:
                    self.datas.append((a, b, 'DATA'))

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
                hooks_cache.remove(applied_hooks)
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
        assert len(self.pure) == 0
        self.pure =  self.graph.make_a_TOC(['PYMODULE'])
        # And get references to module code objects constructed by ModuleGraph
        # to avoid writing .pyc/pyo files to hdd.
        self.pure._code_cache = self.graph.get_code_objects()

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
