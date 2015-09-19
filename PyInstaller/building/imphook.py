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
import warnings

from .. import log as logging
from .utils import format_binaries_and_datas
from ..compat import importlib_load_source, UserDict
from ..utils.misc import get_code_object

logger = logging.getLogger(__name__)


class HooksCache(UserDict):
    """
    Implements cache of module list for which there exists a hook.
    It allows to iterate over import hooks and remove them.
    """
    def __init__(self, hooks_path):
        """
        :param hooks_path: File name where to load hook from.
        """
        # Initializes self.data that contains the real dictionary.
        UserDict.__init__(self)
        self._load_file_list(hooks_path)

    def _load_file_list(self, path):
        """
        Internal method list directory and update the list of available hooks.
        """
        files = glob.glob(os.path.join(path, 'hook-*.py'))
        for f in files:
            # Remove prefix 'hook-' and suffix '.py'.
            modname = os.path.basename(f)[5:-3]
            f = os.path.abspath(f)
            # key - module name, value - path to hook directory.
            self.data[modname] = f

    def add_custom_paths(self, custom_paths):
        for p in custom_paths:
            self._load_file_list(p)

    def remove(self, names):
        """
        :param names: List of module names to remove from cache.
        """
        names = set(names)  # Eliminate duplicate entries.
        for n in names:
            if n in self.data:
                del self.data[n]


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


# TODO Simplify this class and drop useless code.
# TODO This class should raise exceptions on external callers attempting to
# modify class attributes (e.g., a hook attempting to set "mod.datas = []").
# This has been the source of numerous difficult-to-debug issues. The simplest
# means of ensuring this would be to:
#
# * Prefix all attribute names by "_" (e.g., renaming "datas" to "_datas").
# * Define one @property-decorated getter (but not setter) for each such
#   attribute, thus permitting access but prohibiting modification.
# TODO There is no method resembling info() in the ModuleGraph class. Correct
# the docstring below.
class FakeModule(object):
    """
    A **mod** (i.e., metadata describing external assets to be frozen with an
    imported module).

    Mods are both passed to and returned from the `hook(mod)` functions of
    `hook-{module_name}.py` files. Mods are constructed before the call from
    `ModuleGraph` info. Changes to mods are propagated back to the current graph
    and related data structures.

    .. NOTE::
       Mods are *only* used for communication with hooks.

    Attributes
    ----------
    Hook functions may access but *not* modify the following attributes:

    __file__ : str
        Absolute path of this module's Python file. (Unlike all other
        attributes, hook functions may modify this attribute.)
    __path__ : str
        Absolute path of this module's parent directory.
    name : str
        This module's `.`-delimited name (e.g., `six.moves.tkinter`).
    co : code
        Code object compiled from the contents of `__file__` (e.g., via the
        `compile()` builtin).
    datas : list
        List of associated data files.
    imports : list
        List of things this module imports.
    binaries : list
        List of `(name, path, 'BINARY')` tuples or TOC objects.
    """

    def __init__(self, identifier, graph):
        # Go into the module graph and get the node for this identifier.
        # It should always exist because the caller should be working
        # from the graph itself, or a TOC made from the graph.
        node = graph.findNode(identifier)
        assert(node is not None) # should not occur
        # TODO: Rename self.name into self.__name__, like normal
        # modules have
        self.name = identifier
        self.__name__ = identifier
        # keep a pointer back to the original node
        self.node = node
        # keep a pointer back to the original graph
        self.graph = graph
        # Add the __file__ member
        self.__file__ = node.filename
        # Add the __path__ member which is either None or, if
        # the node type is Package, a list of one element, the
        # path string to the package directory -- just like a mod.
        # Note that if the hook changes it, it will change in the node proper.
        self.__path__ = node.packagepath
        # Stick in the .co (compiled code) member. One hook (hook-distutiles)
        # wants to change both __path__ and .co. TODO: HOW HANDLE?
        self.co = node.code
        # Create the datas member as an empty list
        self.datas = []
        # Add the binaries and imports lists and populate with names.
        # The node imports whatever is reachable in the graph
        # starting at that node. Put Extension names in binaries.
        self.binaries = []
        self.imports = []
        for impnode in graph.flatten(start=node):
            if type(impnode).__name__ != 'Extension' :
                self.imports.append([impnode.identifier, 1, 0, -1])
            else:
                self.binaries.append([(impnode.identifier, impnode.filename, 'BINARY')])
        # Private members to collect changes.
        self._added_imports = []
        self._deleted_imports = []
        self._added_binaries = []

    def add_import(self,names):
        """
        Add all Python modules whose `.`-delimited names are in the passed list
        as "hidden imports" upon which the current module depends.

        The passed argument may be either a list of module names *or* a single
        module name.
        """
        warnings.warn("Deprecated: Use the hook's attribute `hiddenimports'",
                      DeprecationWarning)
        if not isinstance(names, list):
            names = [names]  # Allow passing string or list.
        self._added_imports.extend(names) # save change to implement in graph later
        for name in names:
            self.imports.append([name,1,0,-1]) # make change visible to caller

    def del_import(self,names):
        """
        Remove all Python modules whose `.`-delimited names are in the passed
        list from the set of imports (either hidden or visible) upon which the
        current module depends.

        The passed argument may be either a list of module names *or* a single
        module name.
        """
        warnings.warn("Deprecated: Use the hook's attribute `excludedimports'",
                      DeprecationWarning)
        # just save to implement in graph later
        if not isinstance(names, list):
            names = [names]  # Allow passing string or list.
        self._deleted_imports.extend(names)

    def retarget(self, path_to_new_code):
        """
        Recompile this module's code object as the passed Python file.

        This method is intended to "retarget" unfreezable modules into simpler
        versions well-suited to being frozen. This is especially useful for
        **venvs** (i.e., virtual environments), which frequently override
        default modules with wrappers poorly suited to being frozen.
        """
        # Keep the original filename in the fake code object.
        new_code = get_code_object(path_to_new_code, new_filename=self.node.filename)
        # Update node.
        # TODO Need to update many attributes more, e.g. node.globalnames.
        # Perhaps it's better to replace the node
        self.node.code = new_code
        self.node.filename = path_to_new_code
        # Update dependencies in the graph.
        self.graph._scan_code(new_code, self.node)


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
        self._module = importlib_load_source('pyi_hook.'+self._name, self._filename)
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
        # TODO use directly Modulegraph machinery in the 'def hook(mod)' function.
        # TODO: it won't be called "FakeModule" later on
        # Process a hook(mod) function. Create a Module object as its API.
        mod = FakeModule(self._name, mod_graph)
        mod = self._module.hook(mod)

        for item in mod._added_imports:
            self._process_one_hiddenimport(item, mod_graph)
        for item in mod.datas:
            # Supposed to be TOC form (n,p,'DATA')
            assert(item[2] == 'DATA')
            self.datas.add(item[0:2])  # Drop element 'DATA'
        for item in mod._deleted_imports:
            # Remove the graph link between the hooked module and item.
            # This removes the 'item' node from the graph if no other
            # links go to it (no other modules import it)
            mod_graph.removeReference(mod.node, item)
        # TODO: process mod.datas if not empty, tkinter data files

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

