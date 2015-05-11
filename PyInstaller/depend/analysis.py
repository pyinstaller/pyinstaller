#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
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

The main extension here over ModuleGraph is a method to extract nodes
from the flattened graph and return them as a TOC, or added to a TOC.
Other added methods look up nodes by identifier and return facts
about them, replacing what the old ImpTracker list could do.
"""


import logging
import os
from PyInstaller import compat as compat
import PyInstaller.utils
from PyInstaller.utils.misc import load_py_data_struct
from modulegraph.modulegraph import ModuleGraph

logger = logging.getLogger(__name__)


class PyiModuleGraph(ModuleGraph):
    def __init__(self, pyi_homepath, *args, **kwargs):
        super(PyiModuleGraph, self).__init__(*args, **kwargs)
        # Dict to map ModuleGraph node types to TOC typecodes
        self.typedict = {
            'Module': 'PYMODULE',
            'SourceModule': 'PYMODULE',
            'CompiledModule': 'PYMODULE',
            'Package': 'PYMODULE',
            'Extension': 'EXTENSION',
            'Script': 'PYSOURCE',
            'BuiltinModule': 'BUILTIN',
            'MissingModule': 'MISSING',
            'does not occur': 'BINARY'
        }
        # Homepath to the place where is PyInstaller located.
        self._homepath = pyi_homepath
        # modulegraph Node for the main python script that is analyzed
        # by PyInstaller.
        self._top_script_node = None
        # Load dict with available run-time hooks.
        self._available_rthooks = load_py_data_struct(
            os.path.join(self._homepath, 'PyInstaller', 'loader', 'rthooks.dat')
        )

    def run_script(self, pathname):
        """
        Wrap the parent's 'run_script' method and create graph from the first
        script in the analysis, and save its node to use as the "caller" node
        for all others. This gives a connected graph rather than a collection
        of unrelated trees,
        """
        if self._top_script_node is None:
            # Remember the node for the first script.
            self._top_script_node = super(PyiModuleGraph, self).run_script(pathname)
            return self._top_script_node
        else:
            return super(PyiModuleGraph, self).run_script(pathname, caller=self._top_script_node)

    def get_code_objects(self):
        """
        Get code objects from ModuleGraph for pure Pyhton modules. This allows
        to avoid writing .pyc/pyo files to hdd at later stage.

        :return: Dict with module name and code object.
        """
        code_dict = {}
        mod_types = set(['Module', 'SourceModule', 'CompiledModule', 'Package'])
        for node in self.flatten():
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

    def make_a_TOC(self, typecode=[], existing_TOC=None):
        """
        Return the name, path and type of selected nodes as a TOC, or appended
        to a TOC. The selection is via a list of PyInstaller TOC typecodes.
        If that list is empty we return the complete flattened graph as a TOC
        with the ModuleGraph note types in place of typecodes -- meant for
        debugging only. Normally we return ModuleGraph nodes whose types map
        to the requested PyInstaller typecode(s) as indicated in the typedict.

        We use the ModuleGraph (really, ObjectGraph) flatten() method to
        scan all the nodes. This is patterned after ModuleGraph.report().
        """
        result = existing_TOC or TOC()
        for node in self.flatten():
            # TODO This is terrible. Everything in Python has a type. It's
            # nonsensical to even speak of "nodes [that] are not typed." How
            # would that even occur? After all, even "None" has a type! (It's
            # "NoneType", for the curious.) Remove this, please.

            # get node type e.g. Script
            mg_type = type(node).__name__
            if mg_type is None:
                continue # some nodes are not typed?
            # translate to the corresponding TOC typecode, or leave as-is
            toc_type = self.typedict.get(mg_type, mg_type)
            # Does the caller care about the typecode?
            if len(typecode):
                # Caller cares, so if there is a mismatch, skip this one
                if not (toc_type in typecode):
                    continue
            # else: caller doesn't care, return ModuleGraph type in typecode
            # Extract the identifier and a path if any.
            if mg_type == 'Script':
                # for Script nodes only, identifier is a whole path
                (name, ext) = os.path.splitext(node.filename)
                name = os.path.basename(name)
            else:
                name = node.identifier
            path = node.filename if node.filename is not None else ''
            # TOC.append the data. This checks for a pre-existing name
            # and skips it if it exists.
            result.append((name, path, toc_type))
        return result

    # Given a list of nodes, create a TOC representing those nodes.
    # This is mainly used to initialize a TOC of scripts with the
    # ones that are runtime hooks. The process is almost the same as
    # make_a_TOC, but the caller guarantees the nodes are
    # valid, so minimal checking.
    def nodes_to_TOC(self, node_list, existing_TOC = None):
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


    def analyze_runtime_hooks(self, priority_scripts, custom_runhooks):
        """
        Analyze custom run-time hooks and run-time hooks implied by found modules.

        Analyze them and update the 'priority_scripts' list.
        """
        logger.info('Analyzing run-time hooks ...')
        # TODO clean up comments in this method.
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

        if custom_runhooks:
            for hook_file in custom_runhooks:
                logger.info("Including custom run-time hook %r", hook_file)
                hook_file = os.path.abspath(hook_file)
                # Not using "try" here because the path is supposed to
                # exist, if it does not, the raised error will explain.
                priority_scripts.insert( RTH_START_POSITION, self.run_script(hook_file))
                rthook_next_position += 1

        # TODO including run-time hooks should be done after processing regular import hooks.
        # Find runtime hooks that are implied by packages already imported.
        # Get a temporary TOC listing all the scripts and packages graphed
        # so far. Assuming that runtime hooks apply only to modules and packages.
        temp_toc = self.make_a_TOC(['EXTENSION', 'PYMODULE', 'PYSOURCE'])
        for (mod_name, path, typecode) in temp_toc:
            # Look if there is any run-time hook for given module.
            if mod_name in self._available_rthooks:
                # There could be several run-time hooks for a module.
                for hook in self._available_rthooks[mod_name]:
                    logger.info("Including run-time hook %r", hook)
                    path = os.path.join(self._homepath, 'PyInstaller', 'loader', 'rthooks', hook)
                    priority_scripts.insert(
                        rthook_next_position,
                        self.run_script(path)
                    )


# TODO Simplify the representation and use directly Modulegraph objects.
class TOC(compat.UserList):
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
        compat.UserList.__init__(self)
        self.filenames = set()
        if initlist:
            for entry in initlist:
                self.append(entry)

    def _normentry(self, entry):
        if not isinstance(entry, tuple):
            logger.info("TOC found a %s, not a tuple", entry)
            raise TypeError("Expected tuple, not %s." % type(entry).__name__)
        name, path, typecode = entry
        if typecode in ["BINARY", "DATA"]:
            # Normalize the case for binary files and data files only (to avoid duplicates
            # for different cases under Windows). We can't do that for
            # Python files because the import semantic (even at runtime)
            # depends on the case.
            name = os.path.normcase(name)
        return (name, path, typecode)

    def append(self, entry):
        name, path, typecode = self._normentry(entry)
        if name not in self.filenames:
            self.data.append((name, path, typecode))
            self.filenames.add(name)

    def insert(self, pos, entry):
        name, path, typecode = self._normentry(entry)
        if name not in self.filenames:
            self.data.insert(pos, (name, path, typecode))
            self.filenames.add(name)

    def __add__(self, other):
        result = TOC(self)
        result.extend(other)
        return result

    def __radd__(self, other):
        result = TOC(other)
        result.extend(self)
        return result

    def extend(self, other):
        for entry in other:
            self.append(entry)

    def __sub__(self, other):
        other = TOC(other)
        filenames = self.filenames - other.filenames
        result = TOC()
        for name, path, typecode in self:
            if name in filenames:
                result.data.append((name, path, typecode))
        return result

    def __rsub__(self, other):
        result = TOC(other)
        return result.__sub__(self)

    def intersect(self, other):
        other = TOC(other)
        filenames = self.filenames.intersection(other.filenames)
        result = TOC()
        for name, path, typecode in other:
            if name in filenames:
                result.data.append((name, path, typecode))
        return result



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
        self.name = identifier
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
        for impnode in graph.flatten(None,node) :
            if type(impnode).__name__ != 'Extension' :
                self.imports.append([impnode.identifier,1,0,-1])
            else:
                self.binaries.append( [(impnode.identifier, impnode.filename, 'BINARY')] )
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
        # just save to implement in graph later
        if not isinstance(names, list):
            names = [names]  # Allow passing string or list.
        self._deleted_imports.extend(names)

    def add_binary(self,list_of_tuples):
        """
        Add all external dynamic libraries in the passed list of TOC-style
        3-tuples as dependencies of the current module.

        The third element of each such tuple *must* be `BINARY`.
        """
        for item in list_of_tuples:
            self._added_binaries.append(item)
            self.binaries.append(item)

    def add_data(self, list_of_tuples):
        """
        Add all external data files in the passed list of TOC-style 3-tuples as
        dependencies of the current module.

        The third element of each such tuple *must* be `DATA`.
        """
        self.datas.extend(list_of_tuples)

    def retarget(self, path_to_new_code):
        """
        Recompile this module's code object as the passed Python file.

        This method is intended to "retarget" unfreezable modules into simpler
        versions well-suited to being frozen. This is especially useful for
        **venvs** (i.e., virtual environments), which frequently override
        default modules with wrappers poorly suited to being frozen.
        """
        # Keep the original filename in the fake code object.
        new_code = PyInstaller.utils.misc.get_code_object(path_to_new_code, new_filename=self.node.filename)
        # Update node.
        self.node.code = new_code
        self.node.filename = path_to_new_code
        # Update dependencies in the graph.
        self.graph.scan_code(new_code, self.node)
