#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Code related to processing of import hooks.
"""

import glob
import os.path
import re
import sys
import warnings

from .. import log as logging
from .utils import format_binaries_and_datas
from ..compat import expand_path
from ..compat import importlib_load_source, UserDict, is_py2
from ..utils.misc import get_code_object
from .imphookapi import PostGraphAPI

logger = logging.getLogger(__name__)


class HooksCache(dict):
    """
    Dictionary mapping from the fully-qualified names of each module hooked by
    at least one hook script to lists of the absolute paths of these scripts.

    This `dict` subclass caches the list of all hooks applicable to each module,
    permitting Pythonic mapping, iteration, addition, and removal of such hooks.
    Each dictionary key is a fully-qualified module name. Each dictionary value
    is a list of the absolute paths of all hook scripts specific to that module,
    including both official PyInstaller hooks and unofficial user-defined hooks.

    See Also
    ----------
    `_load_file_list()`
        For details on hook priority.
    """
    def __init__(self, hooks_dir):
        """
        Initialize this dictionary.

        Parameters
        ----------
        hook_dir : str
            Absolute or relative path of the directory containing hooks with
            which to populate this cache. By default, this is the absolute path
            of the `PyInstaller/hooks` directory containing official hooks.
        """
        super(dict, self).__init__()
        self._load_file_list(hooks_dir)

    def _load_file_list(self, hooks_dir):
        """
        Cache all hooks in the passed directory.

        **Order of caching is significant** with respect to hooks for the same
        module, as the values of this dictionary are ordered lists. Hooks for
        the same module will be run in the order in which they are cached.
        Previously cached hooks are always preserved (rather than overidden).

        Specifically, any hook in the passed directory having the same module
        name as that of a previously cached hook will be appended to the list of
        hooks for that module name. By default, official hooks are cached
        _before_ user-defined hooks. For modules with both official and
        user-defined hooks, this implies that the former take priority over and
        will be run _before_ the latter.

        Parameters
        ----------
        hooks_dir : str
            Absolute or relative path of the directory containing additional
            hooks to be cached. For convenience, tilde and variable expansion
            will be applied to this path (e.g., a leading `~` will be replaced
            by the absolute path of the corresponding home directory).
        """
        # Perform tilde and variable expansion and validate the result.
        hooks_dir = expand_path(hooks_dir)
        if not os.path.isdir(hooks_dir):
            logger.error('Hook directory %r not found',
                         os.path.abspath(hooks_dir))
            return

        # For each hook in the passed directory...
        hook_files = glob.glob(os.path.join(hooks_dir, 'hook-*.py'))
        for hook_file in hook_files:
            # Absolute path of this hook's script.
            hook_file = os.path.abspath(hook_file)

            # Fully-qualified name of this hook's corresponding module,
            # constructed by removing the "hook-" prefix and ".py" suffix.
            module_name = os.path.basename(hook_file)[5:-3]

            # If this module already has cached hooks, append this hook's path
            # to the existing list of such paths.
            if module_name in self:
                self[module_name].append(hook_file)
            # Else, default to a new list containing only this hook's path.
            else:
                self[module_name] = [hook_file]

    def add_custom_paths(self, hooks_dirs):
        """
        Cache all hooks in the list of passed directories.

        Parameters
        ----------
        hooks_dirs : list
            List of the absolute or relative paths of all directories containing
            additional hooks to be cached.
        """
        for hooks_dir in hooks_dirs:
            self._load_file_list(hooks_dir)

    def remove(self, module_names):
        """
        Remove all key-value pairs whose key is a fully-qualified module name in
        the passed list from this dictionary.

        Parameters
        ----------
        module_names : list
            List of all fully-qualified module names to be removed.
        """
        for module_name in set(module_names):  # Eliminate duplicate entries.
            if module_name in self:
                del self[module_name]


# TODO: The "UserDict" class has been obsoleted by subclassing the "dict" class
# directly. Let's consider doing that. Huzzah!
class AdditionalFilesCache(UserDict):
    """
    Cache for storing what binaries and datas were pushed by what modules
    when import hooks were processed.
    """
    def add(self, modname, binaries, datas):
        self.data[modname] = {'binaries': binaries, 'datas': datas}

    def binaries(self, modname):
        """
        Return list of binaries for given module name.
        """
        return self.data[modname]['binaries']

    def datas(self, modname):
        """
        Return list of datas for given module name.
        """
        return self.data[modname]['datas']


class ImportHook(object):
    """
    Class encapsulating processing of hook attributes like hiddenimports, etc.
    """
    def __init__(self, modname, hook_filename):
        """
        :param hook_filename: File name where to load hook from.
        """
        logger.info('Processing hook   %s' % os.path.basename(hook_filename))
        self._name = modname
        self._filename = hook_filename
        # _module represents the code of 'hook-modname.py'
        # Load hook from file and parse and interpret it's content.
        hook_modname = 'PyInstaller_hooks_' + modname.replace('.', '_')
        self._module = importlib_load_source(hook_modname, self._filename)
        # Public import hook attributes for further processing.
        self.binaries = set()
        self.datas = set()

    # Internal methods for processing.

    def _process_hook_function(self, mod_graph):
        """
        Call the hook function hook(mod).
        Function hook(mod) has to be called first because this function
        could update other attributes - datas, hiddenimports, etc.
        """
        # Process a `hook(hook_api)` function.
        hook_api = PostGraphAPI(self._name, mod_graph)
        self._module.hook(hook_api)

        self.datas.update(set(hook_api._added_datas))
        self.binaries.update(set(hook_api._added_binaries))
        for item in hook_api._added_imports:
            self._process_one_hiddenimport(item, mod_graph)
        for item in hook_api._deleted_imports:
            # Remove the graph link between the hooked module and item.
            # This removes the 'item' node from the graph if no other
            # links go to it (no other modules import it)
            mod_graph.removeReference(hook_api.node, item)

    def _process_hiddenimports(self, mod_graph):
        """
        'hiddenimports' is a list of Python module names that PyInstaller
        is not able detect.
        """
        # push hidden imports into the graph, as if imported from self._name
        for item in self._module.hiddenimports:
            self._process_one_hiddenimport(item, mod_graph)

    def _process_one_hiddenimport(self, item, mod_graph):
        try:
            # Do not try to first find out if a module by that name already exist.
            # Rely on modulegraph to handle that properly.
            # Do not automatically create namespace packages if they do not exist.
            caller = mod_graph.findNode(self._name, create_nspkg=False)
            mod_graph.import_hook(item, caller=caller)
        except ImportError:
            # Print warning if a module from hiddenimport could not be found.
            # modulegraph raises ImporError when a module is not found.
            # Import hook with non-existing hiddenimport is probably a stale hook
            # that was not updated for a long time.
            logger.warn("Hidden import '%s' not found (probably old hook)" % item)

    def _remove_module_references(self, node, graph, mod_filter=None):
        """
        Remove implicit reference to a module. Also submodules of the hook name
        might reference the module. Remove those references too.

        :param node:
        :param mod_filter: List of module name prefixes to remove reference to.
        :return: True if all references were removed False otherwise
        """
        result = True  # First assume it is possible to remove all references.
        referers = graph.getReferers(node)  # Nodes that reference 'node'.

        if not mod_filter:
            # Just remove reference, nothing special filtering.
            for r in referers:
                logger.debug('Removing reference %s' % r.identifier)
                graph.removeReference(r, node)
            return True

        # Remove only references that starts with any prefix from 'mod_filter'.
        regex_str = '|'.join(['(%s.*)' % x for x in mod_filter])
        is_allowed = re.compile(regex_str)
        for r in referers:
            if is_allowed.match(r.identifier):
                logger.debug('Removing reference %s' % r.identifier)
                # Contains prefix of 'imported_name' - remove reference.
                graph.removeReference(r, node)
            else:
                # Other modules reference the implicit import - DO NOT remove it.
                # Any module name was not specified in the filder and cannot be
                # removed.
                logger.debug('Removing reference %s failed' % r.identifier)
                result = False

        return result

    def _process_excludedimports(self, mod_graph):
        """
        'excludedimports' is a list of Python module names that PyInstaller
        should not detect as dependency of this module name.
        """
        not_allowed_references = set(self._module.excludedimports)
        # Remove references between module nodes, as if they are not imported from 'name'
        for item in not_allowed_references:
            try:
                excluded_node = mod_graph.findNode(item)
                if excluded_node is not None:
                    logger.info("Excluding import '%s'" % item)

                    safe_to_remove = self._remove_module_references(excluded_node, mod_graph,
                                                                    mod_filter=not_allowed_references)
                    # If no other modules reference the excluded_node then it is safe to remove
                    # all references to excluded_node and its all submodules.
                    # NOTE: Removing references from graph will keep some dead branches that
                    #       are not reachable from the top-level script. But import hoosks
                    #       for modules in dead branches will get processed!
                    # TODO Find out a way to remove unreachable branches in the graph. - Create a new graph object that will be constructed just from the top-level script?
                    if safe_to_remove:
                        submodule_list = set()
                        # First find submodules.
                        for subnode in mod_graph.nodes():
                            if subnode.identifier.startswith(excluded_node.identifier + '.'):
                                submodule_list.add(subnode)
                        # Then remove references to those submodules.
                        for mod in submodule_list:
                            mod_referers = mod_graph.getReferers(mod)
                            for mod_ref in mod_referers:
                                mod_graph.removeReference(mod_ref, mod)
                            logger.warn("  Removing import '%s'" % mod.identifier)
                            mod_graph.removeNode(mod)
                        # Remove the parent node itself.
                        logger.warn("  Removing import '%s'" % item)
                        mod_graph.removeNode(excluded_node)

                else:
                    logger.info("Excluded import '%s' not found" % item)
            except ImportError:
                # excludedimport could not be found.
                # modulegraph raises ImporError when a module is not found.
                logger.info("Excluded import '%s' not found" % item)

    def _process_datas(self, mod_graph):
        """
        'datas' is a list of globs of files or
        directories to bundle as datafiles. For each
        glob, a destination directory is specified.
        """
        # Find all files and interpret glob statements.
        self.datas.update(set(format_binaries_and_datas(self._module.datas)))

    def _process_binaries(self, mod_graph):
        """
        'binaries' is a list of files to bundle as binaries.
        Binaries are special that PyInstaller will check if they
        might depend on other dlls (dynamic libraries).
        """
        self.binaries.update(set(format_binaries_and_datas(self._module.binaries)))

    def _process_attrs(self, mod_graph):
        # TODO implement attribute 'hook_name_space.attrs'
        # hook_name_space.attrs is a list of tuples (attr_name, value) where 'attr_name'
        # is name for Python module attribute that should be set/changed.
        # 'value' is the value of that attribute. PyInstaller will modify
        # mod.attr_name and set it to 'value' for the created .exe file.
        pass

    # Public methods

    def update_dependencies(self, mod_graph):
        """
        Update module dependency graph with import hook attributes (hiddenimports, etc.)
        :param mod_graph: PyiModuleGraph object to be updated.
        """
        if hasattr(self._module, 'hook'):
            self._process_hook_function(mod_graph)
        if hasattr(self._module, 'hiddenimports'):
            self._process_hiddenimports(mod_graph)
        if hasattr(self._module, 'excludedimports'):
            self._process_excludedimports(mod_graph)
        if hasattr(self._module, 'datas'):
            self._process_datas(mod_graph)
        if hasattr(self._module, 'binaries'):
            self._process_binaries(mod_graph)
        if hasattr(self._module, 'attrs'):
            self._process_attrs(mod_graph)
