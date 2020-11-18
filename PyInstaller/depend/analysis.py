#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

"""
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
 ExtensionPackage basename         full path to __init__.{so,dll}
        packagepath is ['path to package']

The main extension here over ModuleGraph is a method to extract nodes
from the flattened graph and return them as a TOC, or added to a TOC.
Other added methods look up nodes by identifier and return facts
about them, replacing what the old ImpTracker list could do.
"""

import os
import re
import sys
import traceback
import ast

from copy import deepcopy
from collections import defaultdict

from .. import compat
from .. import HOMEPATH, PACKAGEPATH
from .. import log as logging
from ..log import INFO, DEBUG, TRACE
from ..building.datastruct import TOC
from .imphook import AdditionalFilesCache, ModuleHookCache
from .imphookapi import PreSafeImportModuleAPI, PreFindModulePathAPI
from ..compat import importlib_load_source, PY3_BASE_MODULES,\
        PURE_PYTHON_MODULE_TYPES, BINARY_MODULE_TYPES, VALID_MODULE_TYPES, \
        BAD_MODULE_TYPES, MODULE_TYPES_TO_TOC_DICT
from ..lib.modulegraph.find_modules import get_implies
from ..lib.modulegraph.modulegraph import ModuleGraph
from ..utils.hooks import collect_submodules, is_package


logger = logging.getLogger(__name__)


class PyiModuleGraph(ModuleGraph):
    """
    Directed graph whose nodes represent modules and edges represent
    dependencies between these modules.

    This high-level subclass wraps the lower-level `ModuleGraph` class with
    support for graph and runtime hooks. While each instance of `ModuleGraph`
    represents a set of disconnected trees, each instance of this class *only*
    represents a single connected tree whose root node is the Python script
    originally passed by the user on the command line. For that reason, while
    there may (and typically do) exist more than one `ModuleGraph` instance,
    there typically exists only a singleton instance of this class.

    Attributes
    ----------
    _hooks : ModuleHookCache
        Dictionary mapping the fully-qualified names of all modules with
        normal (post-graph) hooks to the absolute paths of such hooks. See the
        the `_find_module_path()` method for details.
    _hooks_pre_find_module_path : ModuleHookCache
        Dictionary mapping the fully-qualified names of all modules with
        pre-find module path hooks to the absolute paths of such hooks. See the
        the `_find_module_path()` method for details.
    _hooks_pre_safe_import_module : ModuleHookCache
        Dictionary mapping the fully-qualified names of all modules with
        pre-safe import module hooks to the absolute paths of such hooks. See
        the `_safe_import_module()` method for details.
    _user_hook_dirs : list
        List of the absolute paths of all directories containing user-defined
        hooks for the current application.
    _excludes : list
        List of module names to be excluded when searching for dependencies.
    _additional_files_cache : AdditionalFilesCache
        Cache of all external dependencies (e.g., binaries, datas) listed in
        hook scripts for imported modules.
    _base_modules: list
        Dependencies for `base_library.zip` (which remain the same for every
        executable).
    """

    # Note: these levels are completely arbitrary and may be adjusted if needed.
    LOG_LEVEL_MAPPING = {0: INFO, 1: DEBUG, 2: TRACE, 3: TRACE, 4: TRACE}

    def __init__(self, pyi_homepath, user_hook_dirs=(), excludes=(), **kwargs):
        super(PyiModuleGraph, self).__init__(excludes=excludes, **kwargs)
        # Homepath to the place where is PyInstaller located.
        self._homepath = pyi_homepath
        # modulegraph Node for the main python script that is analyzed
        # by PyInstaller.
        self._top_script_node = None

        # Absolute paths of all user-defined hook directories.
        self._excludes = excludes
        self._reset(user_hook_dirs)
        self._analyze_base_modules()

    def _reset(self, user_hook_dirs):
        """
        Reset for another set of scripts.
        This is primary required for running the test-suite.
        """
        self._top_script_node = None
        self._additional_files_cache = AdditionalFilesCache()
        # Command line, Entry Point, and then builtin hook dirs.
        self._user_hook_dirs = (
            list(user_hook_dirs) + [os.path.join(PACKAGEPATH, 'hooks')]
        )
        # Hook-specific lookup tables.
        # These need to reset when reusing cached PyiModuleGraph to avoid
        # hooks to refer to files or data from another test-case.
        logger.info('Caching module graph hooks...')
        self._hooks = self._cache_hooks("")
        self._hooks_pre_safe_import_module = self._cache_hooks('pre_safe_import_module')
        self._hooks_pre_find_module_path = self._cache_hooks('pre_find_module_path')

        # Search for run-time hooks in all hook directories.
        self._available_rthooks = defaultdict(list)
        for uhd in self._user_hook_dirs:
            uhd_path = os.path.abspath(os.path.join(uhd, 'rthooks.dat'))
            try:
                with compat.open_file(uhd_path, compat.text_read_mode,
                                      encoding='utf-8') as f:
                    rthooks = ast.literal_eval(f.read())
            except FileNotFoundError:
                # Ignore if this hook path doesn't have run-time hooks.
                continue
            except Exception as e:
                logger.error('Unable to read run-time hooks from %r: %s' %
                             (uhd_path, e))
                continue

            self._merge_rthooks(rthooks, uhd, uhd_path)

        # Convert back to a standard dict.
        self._available_rthooks = dict(self._available_rthooks)

    def _merge_rthooks(self, rthooks, uhd, uhd_path):
        """The expected data structure for a run-time hook file is a Python
        dictionary of type ``Dict[str, List[str]]`` where the dictionary
        keys are module names the the sequence strings are Python file names.

        Check then merge this data structure, updating the file names to be
        absolute.
        """
        # Check that the root element is a dict.
        assert isinstance(rthooks, dict), (
            'The root element in %s must be a dict.' % uhd_path)
        for module_name, python_file_name_list in rthooks.items():
            # Ensure the key is a string.
            assert isinstance(module_name, compat.string_types), (
                '%s must be a dict whose keys are strings; %s '
                'is not a string.' % (uhd_path, module_name))
            # Ensure the value is a list.
            assert isinstance(python_file_name_list, list), (
                'The value of %s key %s must be a list.' %
                (uhd_path, module_name))
            if module_name in self._available_rthooks:
                logger.warning(
                    'Runtime hooks for %s have already been defined. Skipping '
                    'the runtime hooks for %s that are defined in %s.',
                    module_name, module_name, os.path.join(uhd, 'rthooks')
                )
                # Skip this module
                continue
            # Merge this with existing run-time hooks.
            for python_file_name in python_file_name_list:
                # Ensure each item in the list is a string.
                assert isinstance(python_file_name, compat.string_types), (
                    '%s key %s, item %r must be a string.' %
                    (uhd_path, module_name, python_file_name))
                # Transform it into an absolute path.
                abs_path = os.path.join(uhd, 'rthooks', python_file_name)
                # Make sure this file exists.
                assert os.path.exists(abs_path), (
                    'In %s, key %s, the file %r expected to be located at '
                    '%r does not exist.' %
                    (uhd_path, module_name, python_file_name, abs_path))
                # Merge it.
                self._available_rthooks[module_name].append(abs_path)


    @staticmethod
    def _findCaller(*args, **kwargs):
        # Used to add an additional stack-frame above logger.findCaller.
        # findCaller expects the caller to be three stack-frames above itself.
        return logger.findCaller(*args, **kwargs)

    def msg(self, level, s, *args):
        """
        Print a debug message with the given level.

        1. Map the msg log level to a logger log level.
        2. Generate the message format (the same format as ModuleGraph)
        3. Find the caller, which findCaller expects three stack-frames above
           itself:
            [3] caller -> [2] msg (here) -> [1] _findCaller -> [0] logger.findCaller
        4. Create a logRecord with the caller's information.
        5. Handle the logRecord.
        """
        try:
            level = self.LOG_LEVEL_MAPPING[level]
        except KeyError:
            return
        if not logger.isEnabledFor(level):
            return

        msg = "%s %s" % (s, ' '.join(map(repr, args)))

        try:
            fn, lno, func, sinfo = self._findCaller()
        except ValueError:  # pragma: no cover
            fn, lno, func, sinfo = "(unknown file)", 0, "(unknown function)", None
        record = logger.makeRecord(
            logger.name, level, fn, lno, msg, [], None, func, None, sinfo)

        logger.handle(record)

    # Set logging methods so that the stack is correctly detected.
    msgin = msg
    msgout = msg

    def _cache_hooks(self, hook_type):
        """
        Get a cache of all hooks of the passed type.

        The cache will include all official hooks defined by the PyInstaller
        codebase _and_ all unofficial hooks defined for the current application.

        Parameters
        ----------
        hook_type : str
            Type of hooks to be cached, equivalent to the basename of the
            subpackage of the `PyInstaller.hooks` package containing such hooks
            (e.g., `post_create_package` for post-create package hooks).
        """
        # Cache of this type of hooks.
        # logger.debug("Caching system %s hook dir %r" % (hook_type, system_hook_dir))
        hook_dirs = []
        for user_hook_dir in self._user_hook_dirs:
            # Absolute path of the user-defined subdirectory of this hook type.
            # If this directory exists, add it to the list to be cached.
            user_hook_type_dir = os.path.join(user_hook_dir, hook_type)
            if os.path.isdir(user_hook_type_dir):
                # logger.debug("Caching user %s hook dir %r" % (hook_type, hooks_user_dir))
                hook_dirs.append(user_hook_type_dir)

        return ModuleHookCache(self, hook_dirs)


    def _analyze_base_modules(self):
        """
        Analyze dependencies of the the modules in base_library.zip.
        """
        logger.info('Analyzing base_library.zip ...')
        required_mods = []
        # Collect submodules from required modules in base_library.zip.
        for m in PY3_BASE_MODULES:
            if is_package(m):
                required_mods += collect_submodules(m)
            else:
                required_mods.append(m)
        # Initialize ModuleGraph.
        self._base_modules = [mod
            for req in required_mods
            for mod in self.import_hook(req)]


    def run_script(self, pathname, caller=None):
        """
        Wrap the parent's 'run_script' method and create graph from the first
        script in the analysis, and save its node to use as the "caller" node
        for all others. This gives a connected graph rather than a collection
        of unrelated trees,
        """
        if self._top_script_node is None:
            # Remember the node for the first script.
            try:
                self._top_script_node = super(PyiModuleGraph, self).run_script(
                    pathname)
            except SyntaxError:
                print("\nSyntax error in", pathname, file=sys.stderr)
                formatted_lines = traceback.format_exc().splitlines(True)
                print(*formatted_lines[-4:], file=sys.stderr)
                sys.exit(1)
            # Create references from the top script to the base_modules in graph.
            for node in self._base_modules:
                self.createReference(self._top_script_node, node)
            # Return top-level script node.
            return self._top_script_node
        else:
            if not caller:
                # Defaults to as any additional script is called from the
                # top-level script.
                caller = self._top_script_node
            return super(PyiModuleGraph, self).run_script(
                pathname, caller=caller)


    def process_post_graph_hooks(self):
        """
        For each imported module, run this module's post-graph hooks if any.
        """
        # For each iteration of the infinite "while" loop below:
        #
        # 1. All hook() functions defined in cached hooks for imported modules
        #    are called. This may result in new modules being imported (e.g., as
        #    hidden imports) that were ignored earlier in the current iteration:
        #    if this is the case, all hook() functions defined in cached hooks
        #    for these modules will be called by the next iteration.
        # 2. All cached hooks whose hook() functions were called are removed
        #    from this cache. If this cache is empty, no hook() functions will
        #    be called by the next iteration and this loop will be terminated.
        # 3. If no hook() functions were called, this loop is terminated.
        logger.info('Processing module hooks...')
        while True:
            # Set of the names of all imported modules whose post-graph hooks
            # are run by this iteration, preventing the next iteration from re-
            # running these hooks. If still empty at the end of this iteration,
            # no post-graph hooks were run; thus, this loop will be terminated.
            hooked_module_names = set()

            # For each remaining hookable module and corresponding hooks...
            for module_name, module_hooks in self._hooks.items():
                # Graph node for this module if imported or "None" otherwise.
                module_node = self.findNode(
                    module_name, create_nspkg=False)

                # If this module has not been imported, temporarily ignore it.
                # This module is retained in the cache, as a subsequently run
                # post-graph hook could import this module as a hidden import.
                if module_node is None:
                    continue

                # If this module is unimportable, permanently ignore it.
                if type(module_node).__name__ not in VALID_MODULE_TYPES:
                    hooked_module_names.add(module_name)
                    continue

                # For each hook script for this module...
                for module_hook in module_hooks:
                    # Run this script's post-graph hook.
                    module_hook.post_graph()

                    # Cache all external dependencies listed by this script
                    # after running this hook, which could add dependencies.
                    self._additional_files_cache.add(
                        module_name,
                        module_hook.binaries,
                        module_hook.datas)

                # Prevent this module's hooks from being run again.
                hooked_module_names.add(module_name)

            # Prevent all post-graph hooks run above from being run again by the
            # next iteration.
            self._hooks.remove_modules(*hooked_module_names)

            # If no post-graph hooks were run, terminate iteration.
            if not hooked_module_names:
                break

    def _safe_import_module(self, module_basename, module_name, parent_package):
        """
        Create a new graph node for the module with the passed name under the
        parent package signified by the passed graph node.

        This method wraps the superclass method with support for pre-import
        module hooks. If such a hook exists for this module (e.g., a script
        `PyInstaller.hooks.hook-{module_name}` containing a function
        `pre_safe_import_module()`), that hook will be run _before_ the
        superclass method is called.

        Pre-Safe-Import-Hooks are performed just *prior* to importing
        the module. When running the hook, the modules parent package
        has already been imported and ti's `__path__` is set up. But
        the module is just about to be imported.

        See the superclass method for description of parameters and
        return value.
        """
        # If this module has pre-safe import module hooks, run these first.
        if module_name in self._hooks_pre_safe_import_module:
            # For the absolute path of each such hook...
            for hook in self._hooks_pre_safe_import_module[module_name]:
                # Dynamically import this hook as a fabricated module.
                logger.info('Processing pre-safe import module hook %s '
                            'from %r.', module_name, hook.hook_filename)
                hook_module_name = 'PyInstaller_hooks_pre_safe_import_module_' + module_name.replace('.', '_')
                hook_module = importlib_load_source(hook_module_name,
                                                    hook.hook_filename)

                # Object communicating changes made by this hook back to us.
                hook_api = PreSafeImportModuleAPI(
                    module_graph=self,
                    module_basename=module_basename,
                    module_name=module_name,
                    parent_package=parent_package,
                )

                # Run this hook, passed this object.
                if not hasattr(hook_module, 'pre_safe_import_module'):
                    raise NameError(
                        'pre_safe_import_module() function not defined by '
                        'hook %r.' % hook_module
                    )
                hook_module.pre_safe_import_module(hook_api)

                # Respect method call changes requested by this hook.
                module_basename = hook_api.module_basename
                module_name = hook_api.module_name

            # Prevent subsequent calls from rerunning these hooks.
            del self._hooks_pre_safe_import_module[module_name]

        # Call the superclass method.
        return super(PyiModuleGraph, self)._safe_import_module(
            module_basename, module_name, parent_package)

    def _find_module_path(self, fullname, module_name, search_dirs):
        """
        Get a 3-tuple detailing the physical location of the module with the
        passed name if that module exists _or_ raise `ImportError` otherwise.

        This method wraps the superclass method with support for pre-find module
        path hooks. If such a hook exists for this module (e.g., a script
        `PyInstaller.hooks.hook-{module_name}` containing a function
        `pre_find_module_path()`), that hook will be run _before_ the
        superclass method is called.

        See superclass method for parameter and return value descriptions.
        """
        # If this module has pre-find module path hooks, run these first.
        if fullname in self._hooks_pre_find_module_path:
            # For the absolute path of each such hook...
            for hook in self._hooks_pre_find_module_path[fullname]:
                # Dynamically import this hook as a fabricated module.
                logger.info('Processing pre-find module path hook %s from %r.',
                            fullname, hook.hook_filename)
                hook_fullname = 'PyInstaller_hooks_pre_find_module_path_' + fullname.replace('.', '_')
                hook_module = importlib_load_source(hook_fullname,
                                                    hook.hook_filename)

                # Object communicating changes made by this hook back to us.
                hook_api = PreFindModulePathAPI(
                    module_graph=self,
                    module_name=fullname,
                    search_dirs=search_dirs,
                )

                # Run this hook, passed this object.
                if not hasattr(hook_module, 'pre_find_module_path'):
                    raise NameError(
                        'pre_find_module_path() function not defined by '
                        'hook %r.' % hook_module
                    )
                hook_module.pre_find_module_path(hook_api)

                # Respect method call changes requested by this hook.
                search_dirs = hook_api.search_dirs

            # Prevent subsequent calls from rerunning these hooks.
            del self._hooks_pre_find_module_path[fullname]

        # Call the superclass method.
        return super(PyiModuleGraph, self)._find_module_path(
            fullname, module_name, search_dirs)

    def get_code_objects(self):
        """
        Get code objects from ModuleGraph for pure Pyhton modules. This allows
        to avoid writing .pyc/pyo files to hdd at later stage.

        :return: Dict with module name and code object.
        """
        code_dict = {}
        mod_types = PURE_PYTHON_MODULE_TYPES
        for node in self.flatten(start=self._top_script_node):
            # TODO This is terrible. To allow subclassing, types should never be
            # directly compared. Use isinstance() instead, which is safer,
            # simpler, and accepts sets. Most other calls to type() in the
            # codebase should also be refactored to call isinstance() instead.

            # get node type e.g. Script
            mg_type = type(node).__name__
            if mg_type in mod_types:
                if node.code:
                    code_dict[node.identifier] = node.code
        return code_dict

    def _make_toc(self, typecode=None, existing_TOC=None):
        """
        Return the name, path and type of selected nodes as a TOC, or appended
        to a TOC. The selection is via a list of PyInstaller TOC typecodes.
        If that list is empty we return the complete flattened graph as a TOC
        with the ModuleGraph note types in place of typecodes -- meant for
        debugging only. Normally we return ModuleGraph nodes whose types map
        to the requested PyInstaller typecode(s) as indicated in the MODULE_TYPES_TO_TOC_DICT.

        We use the ModuleGraph (really, ObjectGraph) flatten() method to
        scan all the nodes. This is patterned after ModuleGraph.report().
        """
        # Construct regular expression for matching modules that should be
        # excluded because they are bundled in base_library.zip.
        #
        # This expression matches the base module name, optionally followed by
        # a period and then any number of characters. This matches the module name and
        # the fully qualified names of any of its submodules.
        regex_str = '(' + '|'.join(PY3_BASE_MODULES) + r')(\.|$)'
        module_filter = re.compile(regex_str)

        result = existing_TOC or TOC()
        for node in self.flatten(start=self._top_script_node):
            # Skip modules that are in base_library.zip.
            if module_filter.match(node.identifier):
                continue
            entry = self._node_to_toc(node, typecode)
            if entry is not None:
                # TOC.append the data. This checks for a pre-existing name
                # and skips it if it exists.
                result.append(entry)
        return result

    def make_pure_toc(self):
        """
        Return all pure Python modules formatted as TOC.
        """
        # PyInstaller should handle special module types without code object.
        return self._make_toc(PURE_PYTHON_MODULE_TYPES)

    def make_binaries_toc(self, existing_toc):
        """
        Return all binary Python modules formatted as TOC.
        """
        return self._make_toc(BINARY_MODULE_TYPES, existing_toc)

    def make_missing_toc(self):
        """
        Return all MISSING Python modules formatted as TOC.
        """
        return self._make_toc(BAD_MODULE_TYPES)

    @staticmethod
    def _node_to_toc(node, typecode=None):
        # TODO This is terrible. Everything in Python has a type. It's
        # nonsensical to even speak of "nodes [that] are not typed." How
        # would that even occur? After all, even "None" has a type! (It's
        # "NoneType", for the curious.) Remove this, please.

        # get node type e.g. Script
        mg_type = type(node).__name__
        assert mg_type is not None

        if typecode and not (mg_type in typecode):
            # Type is not a to be selected one, skip this one
            return None
        # Extract the identifier and a path if any.
        if mg_type == 'Script':
            # for Script nodes only, identifier is a whole path
            (name, ext) = os.path.splitext(node.filename)
            name = os.path.basename(name)
        elif mg_type == 'ExtensionPackage':
            # package with __init__ module being an extension module
            # This needs to end up as e.g. 'mypkg/__init__.so'.
            # Convert the packages name ('mypkg') into the module name
            # ('mypkg.__init__') *here* to keep special cases away elsewhere
            # (where the module name is converted to a filename).
            name = node.identifier + ".__init__"
        else:
            name = node.identifier
        path = node.filename if node.filename is not None else ''
        # Ensure name is really 'str'. Module graph might return
        # object type 'modulegraph.Alias' which inherits fromm 'str'.
        # But 'marshal.dumps()' function is able to marshal only 'str'.
        # Otherwise on Windows PyInstaller might fail with message like:
        #
        #   ValueError: unmarshallable object
        name = str(name)
        # Translate to the corresponding TOC typecode.
        toc_type = MODULE_TYPES_TO_TOC_DICT[mg_type]
        return (name, path, toc_type)

    def nodes_to_toc(self, node_list, existing_TOC=None):
        """
        Given a list of nodes, create a TOC representing those nodes.
        This is mainly used to initialize a TOC of scripts with the
        ones that are runtime hooks. The process is almost the same as
        _make_toc(), but the caller guarantees the nodes are
        valid, so minimal checking.
        """
        result = existing_TOC or TOC()
        for node in node_list:
            result.append(self._node_to_toc(node))
        return result

    # Return true if the named item is in the graph as a BuiltinModule node.
    # The passed name is a basename.
    def is_a_builtin(self, name) :
        node = self.findNode(name)
        if node is None:
            return False
        return type(node).__name__ == 'BuiltinModule'

    def get_importers(self, name):
        """List all modules importing the module with the passed name.

        Returns a list of (identifier, DependencyIinfo)-tuples. If the names
        module has not yet been imported, this method returns an empty list.

        Parameters
        ----------
        name : str
            Fully-qualified name of the module to be examined.

        Returns
        ----------
        list
            List of (fully-qualified names, DependencyIinfo)-tuples of all
            modules importing the module with the passed fully-qualified name.

        """
        def get_importer_edge_data(importer):
            edge = self.graph.edge_by_node(importer, name)
            # edge might be None in case an AliasModule was added.
            if edge is not None:
                return self.graph.edge_data(edge)

        node = self.findNode(name)
        if node is None : return []
        _, importers = self.get_edges(node)
        importers = (importer.identifier
                     for importer in importers
                     if importer is not None)
        return [(importer, get_importer_edge_data(importer))
                for importer in importers]

    # TODO create class from this function.
    def analyze_runtime_hooks(self, custom_runhooks):
        """
        Analyze custom run-time hooks and run-time hooks implied by found modules.

        :return : list of Graph nodes.
        """
        rthooks_nodes = []
        logger.info('Analyzing run-time hooks ...')
        # Process custom runtime hooks (from --runtime-hook options).
        # The runtime hooks are order dependent. First hooks in the list
        # are executed first. Put their graph nodes at the head of the
        # priority_scripts list Pyinstaller-defined rthooks and
        # thus they are executed first.
        if custom_runhooks:
            for hook_file in custom_runhooks:
                logger.info("Including custom run-time hook %r", hook_file)
                hook_file = os.path.abspath(hook_file)
                # Not using "try" here because the path is supposed to
                # exist, if it does not, the raised error will explain.
                rthooks_nodes.append(self.run_script(hook_file))

        # Find runtime hooks that are implied by packages already imported.
        # Get a temporary TOC listing all the scripts and packages graphed
        # so far. Assuming that runtime hooks apply only to modules and packages.
        temp_toc = self._make_toc(VALID_MODULE_TYPES)
        for (mod_name, path, typecode) in temp_toc:
            # Look if there is any run-time hook for given module.
            if mod_name in self._available_rthooks:
                # There could be several run-time hooks for a module.
                for abs_path in self._available_rthooks[mod_name]:
                    logger.info("Including run-time hook %r", abs_path)
                    rthooks_nodes.append(self.run_script(abs_path))

        return rthooks_nodes

    def add_hiddenimports(self, module_list):
        """
        Add hidden imports that are either supplied as CLI option --hidden-import=MODULENAME
        or as dependencies from some PyInstaller features when enabled (e.g. crypto feature).
        """
        assert self._top_script_node is not None
        # Analyze the script's hidden imports (named on the command line)
        for modnm in module_list:
            node = self.findNode(modnm)
            if node is not None:
                logger.debug('Hidden import %r already found', modnm)
            else:
                logger.info("Analyzing hidden import %r", modnm)
                # ModuleGraph throws ImportError if import not found
                try:
                    nodes = self.import_hook(modnm)
                    assert len(nodes) == 1
                    node = nodes[0]
                except ImportError:
                    logger.error("Hidden import %r not found", modnm)
                    continue
            # Create references from the top script to the hidden import,
            # even if found otherwise. Don't waste time checking whether it
            # as actually added by this (test-) script.
            self.createReference(self._top_script_node, node)


    def get_co_using_ctypes(self):
        """
        Find modules that import Python module 'ctypes'.

        Modules that import 'ctypes' probably load a dll that might be
        required for bundling with the executable. Thus these modules' code
        needs then to be searched for patterns like these:

            ctypes.CDLL('libname')
            ctypes.cdll.LoadLibrary('libname')

        :return: Code objects importing `ctypes` and thus need to be scanned
                 for module dependencies.
        """
        co_dict = {}
        pure_python_module_types = PURE_PYTHON_MODULE_TYPES | {'Script',}
        node = self.findNode('ctypes')
        if node:
            referers = self.getReferers(node)
            for r in referers:
                r_ident =  r.identifier
                # Ensure that modulegraph objects has attribute 'code'.
                if type(r).__name__ in pure_python_module_types:
                    if r_ident == 'ctypes' or r_ident.startswith('ctypes.'):
                        # Skip modules of 'ctypes' package.
                        continue
                    co_dict[r.identifier] = r.code
        return co_dict


_cached_module_graph_ = None

def initialize_modgraph(excludes=(), user_hook_dirs=()):
    """
    Create the cached module graph.

    This function might appear weird but is necessary for speeding up
    test runtime because it allows caching basic ModuleGraph object that
    gets created for 'base_library.zip'.

    Parameters
    ----------
    excludes : list
        List of the fully-qualified names of all modules to be "excluded" and
        hence _not_ frozen into the executable.
    user_hook_dirs : list
        List of the absolute paths of all directories containing user-defined
        hooks for the current application or `None` if no such directories were
        specified.

    Returns
    ----------
    PyiModuleGraph
        Module graph with core dependencies.
    """
    # normalize parameters to ensure tuples and make camparism work
    user_hook_dirs = user_hook_dirs or ()
    excludes = excludes or ()

    # If there is a graph cached with the same same excludes, reuse it.
    # See ``PyiModulegraph._reset()`` for why what is reset.
    # This cache is uses primary to speed up the test-suite. Fixture
    # `pyi_modgraph` calls this function with empty excludes, creating
    # a graph suitable for the huge majority of tests.
    global _cached_module_graph_
    if (_cached_module_graph_ and
        _cached_module_graph_._excludes == excludes):
        logger.info('Reusing cached module dependency graph...')
        graph = deepcopy(_cached_module_graph_)
        graph._reset(user_hook_dirs)
        return graph

    logger.info('Initializing module dependency graph...')

    # Construct the initial module graph by analyzing all import statements.
    graph = PyiModuleGraph(
        HOMEPATH,
        excludes=excludes,
        # get_implies() are hidden imports known by modulgraph.
        implies=get_implies(),
        user_hook_dirs=user_hook_dirs,
        )

    if not _cached_module_graph_:
        # Only cache the first graph, see above for explanation.
        logger.info('Caching module dependency graph...')
        # cache a deep copy of the graph
        _cached_module_graph_ = deepcopy(graph)
        # Clear data which does not need to be copied from teh cached graph
        # since it will be reset by ``PyiModulegraph._reset()`` anyway.
        _cached_module_graph_._hooks = None
        _cached_module_graph_._hooks_pre_safe_import_module = None
        _cached_module_graph_._hooks_pre_find_module_path = None

    return graph


def get_bootstrap_modules():
    """
    Get TOC with the bootstrapping modules and their dependencies.
    :return: TOC with modules
    """
    # Import 'struct' modules to get real paths to module file names.
    mod_struct = __import__('struct')
    # Basic modules necessary for the bootstrap process.
    loader_mods = TOC()
    loaderpath = os.path.join(HOMEPATH, 'PyInstaller', 'loader')
    # On some platforms (Windows, Debian/Ubuntu) '_struct' and zlib modules are
    # built-in modules (linked statically) and thus does not have attribute __file__.
    # 'struct' module is required for reading Python bytecode from executable.
    # 'zlib' is required to decompress this bytecode.
    for mod_name in ['_struct', 'zlib']:
        mod = __import__(mod_name)  # C extension.
        if hasattr(mod, '__file__'):
            loader_mods.append((mod_name, os.path.abspath(mod.__file__), 'EXTENSION'))
    # NOTE:These modules should be kept simple without any complicated dependencies.
    loader_mods +=[
        ('struct', os.path.abspath(mod_struct.__file__), 'PYMODULE'),
        ('pyimod01_os_path', os.path.join(loaderpath, 'pyimod01_os_path.pyc'), 'PYMODULE'),
        ('pyimod02_archive',  os.path.join(loaderpath, 'pyimod02_archive.pyc'), 'PYMODULE'),
        ('pyimod03_importers',  os.path.join(loaderpath, 'pyimod03_importers.pyc'), 'PYMODULE'),
        ('pyiboot01_bootstrap', os.path.join(loaderpath, 'pyiboot01_bootstrap.py'), 'PYSOURCE'),
    ]
    return loader_mods
