#-----------------------------------------------------------------------------
# Copyright (c) 2005-2026, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
PyInstaller-specific behavior of the module graph.

The engine in :mod:`.graph` knows how to resolve and scan Python modules.
Everything *on top of* that -- import hooks, run-time hooks, TOC generation,
metadata scanning, base-library analysis -- lives here, as the
:class:`ModuleGraphHooks` mixin that :class:`~.graph.ModuleGraph` inherits
from.

Historically this logic lived in a ``PyiModuleGraph`` subclass of a vendored
third-party ``modulegraph`` library. Now that the graph is written in-tree
for PyInstaller alone, the split has no reason to exist: the mixin is merged
into the one and only ``ModuleGraph``. Keeping it as a *mixin* (rather than
pasting everything into one giant file) simply keeps two concerns readable:

* ``graph.py`` -- "how do imports resolve?" (stable, algorithmic)
* ``hooks.py`` -- "what does PyInstaller do around the analysis?" (changes
  with the hook system, the TOC format, and build requirements)

The mixin is active only when the graph was created with a ``pyi_homepath``
(see :meth:`ModuleGraph.__init__`); the hook caches stay ``None`` otherwise
and every hook-related code path checks for that.
"""

from __future__ import annotations

import ast
import os
import sys
import traceback
from collections import defaultdict
from typing import TYPE_CHECKING

from PyInstaller import PACKAGEPATH
from PyInstaller import log as logging
from PyInstaller.compat import PY3_BASE_MODULES, importlib_load_source
from PyInstaller.depend import bytecode
from PyInstaller.depend.imphook import (
    HOOK_PRIORITY_BUILTIN_HOOKS,
    AdditionalFilesCache,
    ModuleHookCache,
    PostGraphAPI,
    PreFindModulePathAPI,
    PreSafeImportModuleAPI,
)
from PyInstaller.depend.modulegraph.nodes import (
    BAD_MODULE_TYPES,
    BINARY_MODULE_TYPES,
    MODULE_TYPES_TO_TOC_DICT,
    PURE_PYTHON_MODULE_TYPES,
    VALID_MODULE_TYPES,
    ModuleType,
    Node,
)
from PyInstaller.log import DEBUG, INFO, TRACE

if TYPE_CHECKING:
    from types import CodeType
    from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ModuleGraphHooks:
    """
    PyInstaller hook machinery and TOC generation, as a mixin on the graph.

    Every method here assumes it is called on a :class:`~.graph.ModuleGraph`
    instance (``self.nodes``, ``self.import_hook()``, ... all come from the
    engine). The hook caches (``_hooks``, ``_hooks_pre_safe_import_module``,
    ``_hooks_pre_find_module_path``) are ``None`` unless
    :meth:`_setup_hooks` ran, which happens only when the graph is created
    with a ``pyi_homepath``.
    """

    # Note: these levels are completely arbitrary and may be adjusted if needed.
    LOG_LEVEL_MAPPING = {0: INFO, 1: DEBUG, 2: TRACE, 3: TRACE, 4: TRACE}

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    @staticmethod
    def _findCaller(*args, **kwargs):
        # Used to add an additional stack-frame above logger.findCaller.
        # findCaller expects the caller to be three stack-frames above itself.
        return logger.findCaller(*args, **kwargs)

    def msg(self, level, s, *args):
        """
        Emit one of the graph's own debug messages.

        The engine speaks in *graph* debug levels (0-4, matching the old
        modulegraph's verbosity scale); this method maps them onto
        PyInstaller's logger levels so graph chatter appears interleaved
        with the rest of the build log at the right verbosity.
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
        record = logger.makeRecord(logger.name, level, fn, lno, msg, [], None, func, None, sinfo)

        logger.handle(record)

    # Set logging methods so that the stack is correctly detected.
    msgin = msg
    msgout = msg

    # ------------------------------------------------------------------
    # Hook setup
    # ------------------------------------------------------------------

    def _setup_hooks(self, user_hook_dirs):
        """
        Set up the PyInstaller hook machinery on this graph.

        This is the former ``PyiModuleGraph._reset()``. It gathers hook
        directories (user-supplied plus PyInstaller's built-in ones), builds
        the three hook caches the analysis consults, and registers the
        run-time hooks declared by ``rthooks.dat`` files.
        """
        # Per-analysis state; reset here so a cached-and-reused graph does
        # not carry over files or settings from another test-case.
        self._top_script_node = None
        self._additional_files_cache = AdditionalFilesCache()
        self._module_collection_mode: Dict[str, str] = dict()
        self._bindepend_symlink_suppression: Set[str] = set()

        # Hook sources: user-supplied (command-line / spec file), entry-point
        # (upstream hooks, contributed hooks), and built-in hooks. The order
        # does not really matter anymore, because each entry is a
        # (location, priority) tuple and order is determined from the
        # assigned priority (which may also be overridden by hooks
        # themselves).
        self._user_hook_dirs: List[Tuple[str, int]] = [
            *user_hook_dirs,
            (os.path.join(PACKAGEPATH, 'hooks'), HOOK_PRIORITY_BUILTIN_HOOKS),
        ]

        # Hook-specific lookup tables. These need to reset when reusing a
        # cached graph, to avoid hooks referring to files or data from
        # another test-case.
        logger.info('Initializing module graph hook caches...')
        self._hooks = self._cache_hooks("")
        self._hooks_pre_safe_import_module = self._cache_hooks('pre_safe_import_module')
        self._hooks_pre_find_module_path = self._cache_hooks('pre_find_module_path')

        # Search for run-time hooks in all hook directories.
        self._available_rthooks: Dict[str, list] = defaultdict(list)
        for uhd, _ in self._user_hook_dirs:
            uhd_path = os.path.abspath(os.path.join(uhd, 'rthooks.dat'))
            try:
                with open(uhd_path, 'r', encoding='utf-8') as f:
                    rthooks = ast.literal_eval(f.read())
            except FileNotFoundError:
                # Ignore if this hook path doesn't have run-time hooks.
                continue
            except Exception as e:
                logger.error('Unable to read run-time hooks from %r: %s' % (uhd_path, e))
                continue

            self._merge_rthooks(rthooks, uhd, uhd_path)

        # Convert back to a standard dict.
        self._available_rthooks = dict(self._available_rthooks)

    def _merge_rthooks(self, rthooks, uhd, uhd_path):
        """
        The expected data structure for a run-time hook file is a Python dictionary of type ``Dict[str, List[str]]``,
        where the dictionary keys are module names and the sequence strings are Python file names.

        Check then merge this data structure, updating the file names to be absolute.
        """
        # Check that the root element is a dict.
        assert isinstance(rthooks, dict), 'The root element in %s must be a dict.' % uhd_path
        for module_name, python_file_name_list in rthooks.items():
            # Ensure the key is a string.
            assert isinstance(module_name, str), \
                '%s must be a dict whose keys are strings; %s is not a string.' % (uhd_path, module_name)
            # Ensure the value is a list.
            assert isinstance(python_file_name_list, list), \
                'The value of %s key %s must be a list.' % (uhd_path, module_name)
            if module_name in self._available_rthooks:
                logger.warning(
                    'Runtime hooks for %s have already been defined. Skipping the runtime hooks for %s that are '
                    'defined in %s.', module_name, module_name, os.path.join(uhd, 'rthooks')
                )
                # Skip this module
                continue
            # Merge this with existing run-time hooks.
            for python_file_name in python_file_name_list:
                # Ensure each item in the list is a string.
                assert isinstance(python_file_name, str), \
                    '%s key %s, item %r must be a string.' % (uhd_path, module_name, python_file_name)
                # Transform it into an absolute path.
                abs_path = os.path.join(uhd, 'rthooks', python_file_name)
                # Make sure this file exists.
                assert os.path.exists(abs_path), \
                    'In %s, key %s, the file %r expected to be located at %r does not exist.' % \
                    (uhd_path, module_name, python_file_name, abs_path)
                # Merge it.
                self._available_rthooks[module_name].append(abs_path)

    def _cache_hooks(self, hook_type):
        """
        Create a cache of all hooks of the specified type.

        The cache will include all official hooks defined by the PyInstaller codebase _and_ all unofficial hooks
        defined for the current application.

        Parameters
        ----------
        hook_type : str
            Type of hooks to be cached, equivalent to the basename of the subpackage of the `PyInstaller.hooks`
            package containing such hooks (e.g., empty string for standard hooks, `pre_safe_import_module` for
            pre-safe-import-module hooks, `pre_find_module_path` for pre-find-module-path hooks).
        """
        # Cache of this type of hooks.
        hook_dirs = []
        for user_hook_dir, priority in self._user_hook_dirs:
            # Absolute path of the user-defined subdirectory of this hook type. If this directory exists, add it to
            # the list to be cached.
            user_hook_type_dir = os.path.join(user_hook_dir, hook_type)
            if os.path.isdir(user_hook_type_dir):
                hook_dirs.append((user_hook_type_dir, priority))

        return ModuleHookCache(self, hook_dirs)

    def _analyze_base_modules(self):
        """
        Analyze dependencies of the modules in base_library.zip.

        Modules shipped in ``base_library.zip`` (the stdlib subset every
        frozen app starts with) do not need to appear in the PYZ; knowing
        their graph nodes up-front lets TOC generation leave them out.
        """
        logger.info('Analyzing modules for base_library.zip ...')
        from PyInstaller.utils.hooks import collect_submodules, is_package

        required_mods = []
        # Collect submodules of the required stdlib packages.
        for m in PY3_BASE_MODULES:
            if is_package(m):
                required_mods += collect_submodules(m)
            else:
                required_mods.append(m)
        # Analyze them; import_hook() raises for unresolvable base modules,
        # which is the desired behavior -- a missing base module means the
        # resulting executable cannot work.
        self._base_modules = [mod for req in required_mods for mod in self.import_hook(req)]

    # ------------------------------------------------------------------
    # Script roots
    # ------------------------------------------------------------------

    def add_script(self, pathname, caller=None):
        """
        Wrap the engine's ``add_script`` with PyInstaller-specific behavior:

        * The first script added becomes the graph's top-level node, and all
          base-library modules are attached below it. That turns what would
          otherwise be a collection of unrelated trees into one connected
          graph rooted at the user's entry point.
        * Syntax errors in the analyzed script terminate the build with a
          readable message instead of a raw traceback.
        """
        try:
            node = super().add_script(pathname)
        except SyntaxError:
            print("\nSyntax error in", pathname, file=sys.stderr)
            formatted_lines = traceback.format_exc().splitlines(True)
            print(*formatted_lines[-4:], file=sys.stderr)
            sys.exit(1)

        if self._top_script_node is None:
            # Remember the node for the first script.
            self._top_script_node = node
            # Create references from the top script to the base modules in
            # the graph, so everything is reachable from the root.
            for base_node in self._base_modules:
                self.add_edge(self._top_script_node, base_node)
        return node

    # ------------------------------------------------------------------
    # Hook extension points, driven by the engine's analysis loop
    # ------------------------------------------------------------------

    def _run_pre_safe_import_hook(self, item):
        """
        Run the ``pre_safe_import_module`` hook for the queued module, if any.

        The hook (loaded from its own file) receives a
        :class:`~PyInstaller.depend.imphook.PreSafeImportModuleAPI` object
        through which it can register runtime modules and packages, alias
        modules, or extend a package's search path -- all before the engine
        resolves the module. Hooks run at most once per module: the cache
        entry is popped.

        :return: The (possibly name-rewritten) queue item to continue with.
        """
        hook = self._hooks_pre_safe_import_module.pop(item.name, None)
        if hook is None:
            return item

        # Dynamically import this hook as a fabricated module.
        hook_path, hook_basename = os.path.split(hook.hook_filename)
        logger.info('Processing pre-safe-import-module hook %r from %r', hook_basename, hook_path)
        hook_module_name = 'PyInstaller_hooks_pre_safe_import_module_' + item.name.replace('.', '_')
        hook_module = importlib_load_source(hook_module_name, hook.hook_filename)

        # Object communicating changes made by this hook back to us.
        hook_api = PreSafeImportModuleAPI(
            module_graph=self,
            module_basename=item.name.rpartition('.')[2],
            module_name=item.name,
            parent_package=self.find_node(item.name.rpartition('.')[0]) if '.' in item.name else None,
        )

        # Run this hook, passed this object.
        if not hasattr(hook_module, 'pre_safe_import_module'):
            raise NameError('pre_safe_import_module() function not defined by hook %r.' % hook_module)
        hook_module.pre_safe_import_module(hook_api)

        # Respect module-name changes requested by this hook. (The old
        # graph also tracked a separate, unqualified basename; the new
        # engine works with fully-qualified names only.)
        if hook_api.module_name != item.name:
            import dataclasses
            item = dataclasses.replace(item, name=hook_api.module_name)

        return item

    def _run_pre_find_module_path_hook(self, hook, fullname):
        """
        Run the ``pre_find_module_path`` hook for the module about to be
        searched for, returning the (possibly hook-adjusted) list of
        directories to search.

        The hook receives a
        :class:`~PyInstaller.depend.imphook.PreFindModulePathAPI` object and
        typically replaces ``api.search_dirs`` to redirect the search for
        the module's file.
        """
        # Dynamically import this hook as a fabricated module.
        hook_path, hook_basename = os.path.split(hook.hook_filename)
        logger.info('Processing pre-find-module-path hook %r from %r', hook_basename, hook_path)
        hook_fullname = 'PyInstaller_hooks_pre_find_module_path_' + fullname.replace('.', '_')
        hook_module = importlib_load_source(hook_fullname, hook.hook_filename)

        # Object communicating changes made by this hook back to us.
        hook_api = PreFindModulePathAPI(
            module_graph=self,
            module_name=fullname,
            search_dirs=self.path,
        )

        # Run this hook, passed this object.
        if not hasattr(hook_module, 'pre_find_module_path'):
            raise NameError('pre_find_module_path() function not defined by hook %r.' % hook_module)
        hook_module.pre_find_module_path(hook_api)

        # Respect search-directory changes requested by this hook.
        return hook_api.search_dirs

    def _find_all_excluded_imports(self, module_name):
        """
        Collect excludedimports from the hooks of the specified module and all its parents.
        """
        excluded_imports = set()
        while module_name:
            # Gather excluded imports from hook belonging to the module.
            module_hook = self._hooks.get(module_name, None)
            if module_hook:
                excluded_imports.update(module_hook.excludedimports)
            # Change module name to the module's parent name
            module_name = module_name.rpartition('.')[0]
        return excluded_imports

    def _check_excluded_import(self, referrer_name, target_name):
        """
        Check whether an import made by ``referrer_name`` is suppressed by
        ``excludedimports`` rules declared in hooks.

        A rule matches when the target's dotted name starts with the rule's
        name (excluding ``PIL`` also excludes ``PIL.Image``). A rule that
        *also* matches the referrer itself is waived: if the referrer is in
        the graph despite the same rule applying to it, some other import
        chain must have overridden the exclusion -- for example, a hook
        excludes a subpackage to keep it out when nothing references it, but
        the user explicitly imports it elsewhere.
        """
        excluded_imports = self._find_all_excluded_imports(referrer_name)
        if not excluded_imports:
            return False

        target_parts = target_name.split('.')
        for excluded_import in excluded_imports:
            rule_parts = excluded_import.split('.')
            if target_parts[:len(rule_parts)] == rule_parts:
                # The referrer is (was!) subject to the same rule.
                referrer_parts = referrer_name.split('.')
                if referrer_parts[:len(rule_parts)] == rule_parts:
                    logger.debug(
                        "Deactivating suppression rule %r for module %r because it also applies to the "
                        "referrer (%r)...", excluded_import, target_name, referrer_name
                    )
                    continue
                return True
        return False

    # ------------------------------------------------------------------
    # Post-graph hook processing
    # ------------------------------------------------------------------

    def process_post_graph_hooks(self, analysis):
        """
        For each imported module, run this module's post-graph hooks if any.

        Parameters
        ----------
        analysis: build_main.Analysis
            The Analysis that calls the hooks

        """
        # For each iteration of the infinite "while" loop below:
        #
        # 1. All hook() functions defined in cached hooks for imported modules are called. This may result in new
        #    modules being imported (e.g., as hidden imports) that were ignored earlier in the current iteration: if
        #    this is the case, all hook() functions defined in cached hooks for these modules will be called by the
        #    next iteration.
        # 2. All cached hooks whose hook() functions were called are removed from this cache. If this cache is empty,
        #    no hook() functions will be called by the next iteration and this loop will be terminated.
        # 3. If no hook() functions were called, this loop is terminated.
        logger.info('Processing module hooks (post-graph stage)...')
        while True:
            # Set of the names of all imported modules whose post-graph hooks are run by this iteration, preventing
            # the next iteration from re-running these hooks. If still empty at the end of this iteration, no
            # post-graph hooks were run; thus, this loop will be terminated.
            hooked_module_names = set()

            # For each remaining hookable module and corresponding hooks...
            for module_name, module_hook in self._hooks.items():
                # Graph node for this module if imported or "None" otherwise.
                module_node = self.find_node(module_name)

                # If this module has not been imported, temporarily ignore it. This module is retained in the cache,
                # as a subsequently run post-graph hook could import this module as a hidden import.
                if module_node is None:
                    continue

                # If this module is unimportable, permanently ignore it.
                if module_node.module_type not in VALID_MODULE_TYPES:
                    hooked_module_names.add(module_name)
                    continue

                # Run this script's post-graph hook.
                module_hook.post_graph(analysis)

                # Cache all external dependencies listed by this script after running this hook, which could add
                # dependencies.
                self._additional_files_cache.add(module_name, module_hook.binaries, module_hook.datas)

                # Update package collection mode settings.
                self._module_collection_mode.update(module_hook.module_collection_mode)

                # Update symbolic link suppression patterns for binary dependency analysis.
                self._bindepend_symlink_suppression.update(module_hook.bindepend_symlink_suppression)

                # Prevent this module's hooks from being run again.
                hooked_module_names.add(module_name)

            # Prevent all post-graph hooks run above from being run again by the next iteration.
            self._hooks.remove_modules(*hooked_module_names)

            # If no post-graph hooks were run, terminate iteration.
            if not hooked_module_names:
                break

    # ------------------------------------------------------------------
    # TOC generation
    # ------------------------------------------------------------------
    # A "TOC" (table of contents) entry is a ``(name, path, typecode)``
    # triple; the typecodes ('PYSOURCE', 'PYMODULE', 'EXTENSION', ...) are
    # part of PyInstaller's serialized build format.

    def get_code_objects(self) -> Dict[str, CodeType]:
        """
        Get code objects from the graph for pure Python modules. This allows
        avoiding writing .pyc/pyo files to disk at a later stage.

        :return: Dict with module name and code object.
        """
        code_dict = {}
        for node in self.iter_graph(start=self._top_script_node):
            if node.module_type in PURE_PYTHON_MODULE_TYPES and node.code is not None:
                code_dict[node.ident] = node.code
        return code_dict

    def _make_toc(self, typecode=None):
        """
        Return the name, path and type of selected nodes as a TOC. The
        selection is determined by the given set of :class:`ModuleType`
        members. If that set is empty/None we return the complete flattened
        graph as a TOC -- meant for debugging only. Normally we return nodes
        whose types map to the requested typecode(s) as indicated in the
        ``MODULE_TYPES_TO_TOC_DICT``.
        """
        toc = list()
        for node in self.iter_graph(start=self._top_script_node):
            entry = self._node_to_toc(node, typecode)
            # Append the entry. We do not check for duplicates here; the TOC
            # normalization is left to the caller. However, as entries are
            # obtained from the graph, there should not be any duplicates at
            # this stage.
            if entry is not None:
                toc.append(entry)
        return toc

    def make_pure_toc(self):
        """
        Return all pure Python modules formatted as TOC.
        """
        # PyInstaller should handle special module types without code object.
        return self._make_toc(PURE_PYTHON_MODULE_TYPES)

    def make_binaries_toc(self):
        """
        Return all binary Python modules formatted as TOC.
        """
        return self._make_toc(BINARY_MODULE_TYPES)

    def make_missing_toc(self):
        """
        Return all MISSING Python modules formatted as TOC.
        """
        return self._make_toc(BAD_MODULE_TYPES)

    @staticmethod
    def _node_to_toc(node: Node, typecode=None):
        """
        Convert one graph node into a TOC entry, or return None if the node's
        type is not among the requested ``typecode`` set.
        """
        if typecode and node.module_type not in typecode:
            # Type is not a to-be-selected one, skip this node.
            return None

        # Extract the identifier and a path, if any.
        if node.module_type == ModuleType.SCRIPT:
            # For Script nodes only, the identifier is a whole path; the TOC
            # name is the bare script name.
            (name, ext) = os.path.splitext(str(node.path))
            name = os.path.basename(name)
        elif (
            node.module_type == ModuleType.EXTENSION and node.spec is not None
            and node.spec.submodule_search_locations
        ):
            # A package whose ``__init__`` is itself an extension module
            # (e.g. ``mypkg/__init__.so``). The package must end up in the
            # bundle as ``mypkg/__init__.so``, so convert the package name
            # ('mypkg') into the module name ('mypkg.__init__') here to keep
            # this special case away from everything else.
            name = node.ident + ".__init__"
        else:
            name = node.ident
        path = str(node.path) if node.path is not None else ''
        return name, path, MODULE_TYPES_TO_TOC_DICT[node.module_type]

    def nodes_to_toc(self, nodes):
        """
        Given a list of nodes, create a TOC representing those nodes. This is
        mainly used to initialize a TOC of scripts with the ones that are
        runtime hooks. The process is almost the same as ``_make_toc()``, but
        the caller guarantees the nodes are valid, so minimal checking.
        """
        return [self._node_to_toc(node) for node in nodes]

    def is_a_builtin(self, name):
        """
        Return True if the named item is in the graph as a builtin module.
        The passed name is a bare module name.
        """
        node = self.find_node(name)
        if node is None:
            return False
        return node.module_type == ModuleType.BUILTIN

    def get_importers(self, name):
        """
        List all modules importing the module with the passed name.

        Returns a list of ``(identifier, dependency_info)``-tuples. If the
        named module has not yet been imported, this method returns an empty
        list. The dependency-info element is always ``None`` in this engine
        (per-edge attributes are not tracked); build warnings treat that as
        a "direct" import.

        Parameters
        ----------
        name : str
            Fully-qualified name of the module to be examined.
        """
        node = self.find_node(name)
        if node is None:
            return []
        return [(importer.ident, None) for importer in self.dependents(node)]

    # ------------------------------------------------------------------
    # Run-time hooks and hidden imports
    # ------------------------------------------------------------------

    def analyze_runtime_hooks(self, custom_runhooks):
        """
        Analyze custom run-time hooks and run-time hooks implied by found
        modules.

        :return: list of graph nodes (the run-time hook scripts).
        """
        rthooks_nodes = []
        logger.info('Analyzing run-time hooks ...')
        # Process custom runtime hooks (from --runtime-hook options). The
        # runtime hooks are order dependent. First hooks in the list are
        # executed first. Put their graph nodes at the head of the
        # priority_scripts list. PyInstaller-defined rthooks are thus
        # executed after the custom ones.
        if custom_runhooks:
            for hook_file in custom_runhooks:
                logger.info("Including custom run-time hook %r", hook_file)
                hook_file = os.path.abspath(hook_file)
                # Not using "try" here because the path is supposed to exist;
                # if it does not, the raised error will explain.
                rthooks_nodes.append(self.add_script(hook_file))

        # Find runtime hooks that are implied by packages already imported.
        # Get a temporary TOC listing all the scripts and packages graphed so
        # far. Assuming that runtime hooks apply only to modules and packages.
        temp_toc = self._make_toc(VALID_MODULE_TYPES)
        for (mod_name, path, typecode) in temp_toc:
            # Look if there is any run-time hook for the given module.
            if mod_name in self._available_rthooks:
                # There could be several run-time hooks for a module.
                for abs_path in self._available_rthooks[mod_name]:
                    hook_path, hook_basename = os.path.split(abs_path)
                    logger.info("Including run-time hook %r from %r", hook_basename, hook_path)
                    rthooks_nodes.append(self.add_script(abs_path))

        return rthooks_nodes

    def add_hiddenimports(self, module_list):
        """
        Add hidden imports that are either supplied as CLI option
        ``--hidden-import=MODULENAME`` or as dependencies from some
        PyInstaller features when enabled (e.g., crypto feature).
        """
        assert self._top_script_node is not None
        # Analyze the script's hidden imports (named on the command line).
        for modnm in module_list:
            node = self.find_node(modnm)
            if node is not None:
                logger.debug('Hidden import %r already found', modnm)
            else:
                logger.info("Analyzing hidden import %r", modnm)
                # import_hook() raises ImportError if the module cannot be
                # resolved (including the case where it is excluded).
                try:
                    nodes = self.import_hook(modnm)
                    assert len(nodes) == 1
                    node = nodes[0]
                except ImportError:
                    logger.error("Hidden import %r not found", modnm)
                    continue
            # Create references from the top script to the hidden import,
            # even if found otherwise. Do not waste time checking whether it
            # is actually added by this (test-) script.
            self.add_edge(self._top_script_node, node)

    # ------------------------------------------------------------------
    # Code/metadata introspection
    # ------------------------------------------------------------------

    def get_code_using(self, module: str) -> "Dict[str, CodeType]":
        """
        Find modules that import a given module.

        :param module: The module you're trying to find dependents for.
        :returns: A dictionary mapping dependent module names to code objects.
        """
        co_dict = {}
        node = self.find_node(module)
        if node is not None:
            for dependent in self.dependents(node):
                if dependent.ident == module or dependent.ident.startswith(module + '.'):
                    # Skip self references or references from the module's own
                    # submodules.
                    continue
                # The code object may be None if the referrer ends up
                # shadowed by an eponymous directory that ends up treated as
                # a namespace package. See #6873 for an example.
                if dependent.code is None:
                    continue
                co_dict[dependent.ident] = dependent.code

        return co_dict

    def metadata_required(self) -> set:
        """
        Collect metadata for all packages that appear to need it.
        """

        # List every function that we can think of which is known to require metadata.
        out = set()

        out |= self._metadata_from(
            "pkg_resources",
            ["get_distribution"],  # Requires metadata for one distribution.
            ["require"],  # Requires metadata for all dependencies.
        )

        # importlib.metadata is often ``import ... as`` aliased to
        # importlib_metadata for compatibility with < py38. Assume both are
        # valid.
        for importlib_metadata in ["importlib.metadata", "importlib_metadata"]:
            out |= self._metadata_from(
                importlib_metadata,
                ["metadata", "distribution", "version", "files", "requires"],
                [],
            )

        return out

    def _metadata_from(self, package, methods=(), recursive_methods=()) -> set:
        """
        Collect metadata whose requirements are implied by given function names.

        Args:
            package:
                The module name that must be imported in a source file to trigger the search.
            methods:
                Function names from **package** which take a distribution name as an argument and imply that metadata
                is required for that distribution.
            recursive_methods:
                Like **methods** but also implies that a distribution's dependencies' metadata must be collected too.
        Returns:
            Required metadata in hook data ``(source, dest)`` format as returned by
            :func:`PyInstaller.utils.hooks.copy_metadata()`.

        Scan all source code to be included for usage of particular *key* functions which imply that that code will
        require metadata for some distribution (which may not be its own) at runtime. In the case of a match,
        collect the required metadata.
        """
        from PyInstaller.utils.hooks import copy_metadata
        from PyInstaller.compat import importlib_metadata

        # Generate sets of possible function names to search for.
        need_metadata = set()
        need_recursive_metadata = set()
        for method in methods:
            need_metadata.update(bytecode.any_alias(package + "." + method))
        for method in recursive_methods:
            need_recursive_metadata.update(bytecode.any_alias(package + "." + method))

        out = set()

        for name, code in self.get_code_using(package).items():
            for calls in bytecode.recursive_function_calls(code).values():
                for function_name, args in calls:
                    # Only consider function calls taking one argument.
                    if len(args) != 1:
                        continue
                    package = args[0]
                    try:
                        if function_name in need_metadata:
                            out.update(copy_metadata(package))
                        elif function_name in need_recursive_metadata:
                            out.update(copy_metadata(package, recursive=True))

                    except importlib_metadata.PackageNotFoundError:
                        # Currently, we opt to silently skip over missing metadata.
                        continue

        return out

    def get_collected_packages(self) -> list:
        """
        Return the list of collected python packages.
        """
        return [
            str(node.ident) for node in self.iter_graph(start=self._top_script_node)
            if node.module_type == ModuleType.PACKAGE
        ]

    def make_hook_binaries_toc(self) -> list:
        """
        Return the TOC list of binaries collected by hooks.
        """
        toc = []
        for node in self.iter_graph(start=self._top_script_node):
            module_name = str(node.ident)
            for dest_name, src_name in self._additional_files_cache.binaries(module_name):
                toc.append((dest_name, src_name, 'BINARY'))

        return toc

    def make_hook_datas_toc(self) -> list:
        """
        Return the TOC list of data files collected by hooks.
        """
        toc = []
        for node in self.iter_graph(start=self._top_script_node):
            module_name = str(node.ident)
            for dest_name, src_name in self._additional_files_cache.datas(module_name):
                toc.append((dest_name, src_name, 'DATA'))

        return toc
