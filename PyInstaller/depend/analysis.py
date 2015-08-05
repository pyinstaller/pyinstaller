#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
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

import glob
import logging
import os
import re

from PyInstaller.building.datastruct import TOC
from ..utils.misc import load_py_data_struct
from ..lib.modulegraph.modulegraph import ModuleGraph
from ..lib.modulegraph.find_modules import get_implies
from ..compat import importlib_load_source, is_py2, PY3_BASE_MODULES
from .. import HOMEPATH
from ..utils.hooks.hookutils import collect_submodules, is_package

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
    _graph_hooks : dict
        Dictionary mapping the fully-qualified names of modules having
        corresponding graph hooks to the absolute paths of these hooks. See the
        `import_module()` method for details.
    """

    # Dict to map ModuleGraph node types to TOC typecodes
    typedict = {
        'Module': 'PYMODULE',
        'SourceModule': 'PYMODULE',
        'CompiledModule': 'PYMODULE',
        'Package': 'PYMODULE',
        'NamespacePackage': 'PYMODULE',
        'Extension': 'EXTENSION',
        'Script': 'PYSOURCE',
        'BuiltinModule': 'BUILTIN',
        'MissingModule': 'MISSING',
        'does not occur': 'BINARY'
    }

    def __init__(self, pyi_homepath, *args, **kwargs):
        super(PyiModuleGraph, self).__init__(*args, **kwargs)
        # Homepath to the place where is PyInstaller located.
        self._homepath = pyi_homepath
        # modulegraph Node for the main python script that is analyzed
        # by PyInstaller.
        self._top_script_node = None

        # Define lookup tables for graph and runtime hooks.
        self._graph_hooks = self._calc_graph_hooks()
        self._available_rthooks = load_py_data_struct(
            os.path.join(self._homepath, 'PyInstaller', 'loader', 'rthooks.dat')
        )

    # TODO Add support for user-defined graph hooks.
    def _calc_graph_hooks(self):
        """
        Initialize the `_graph_hooks` module attribute.
        """
        logger.info('Looking for graph hooks ...')

        # Absolute path of the directory containing graph hooks.
        from PyInstaller.hooks import graph
        graph_hook_dir = graph.__path__[0]

        return {
            os.path.basename(graph_hook_file)[5:-3]: graph_hook_file
            for graph_hook_file in glob.glob(
                os.path.join(graph_hook_dir, 'hook-*.py'))
        }

    def run_script(self, pathname, caller=None):
        """
        Wrap the parent's 'run_script' method and create graph from the first
        script in the analysis, and save its node to use as the "caller" node
        for all others. This gives a connected graph rather than a collection
        of unrelated trees,
        """
        if self._top_script_node is None:
            nodes_without_parent = [x for x in self.flatten()]
            # Remember the node for the first script.
            self._top_script_node = super(PyiModuleGraph, self).run_script(pathname)
            # Create references from top_script to current modules in graph.
            # These modules without parents are dependencies that are necessary
            # for base_library.zip.
            for node in nodes_without_parent:
                self.createReference(self._top_script_node, node)
            # Return top-level script node.
            return self._top_script_node
        else:
            if not caller:
                # Defaults to as any additional script is called from the top-level
                # script.
                caller = self._top_script_node
            return super(PyiModuleGraph, self).run_script(pathname, caller=caller)

    def _import_module(self, partname, fqname, parent):
        """
        Import the Python module with the passed name from the parent package
        signified by the passed graph node.

        This method wraps the superclass method of the same name with support
        for graph hooks. If there exists a corresponding **graph hook** (i.e., a
        module `PyInstaller.hooks.graph.hook-{fqname}`), that hook is imported
        and the `hook()` function necessarily defined by that hook called
        *before* the module with the passed name is imported.

        Parameters
        ----------
        partname : str
            Unqualified name of the module to be imported (e.g., `text`).
        fqname : str
            Fully-qualified name of this module (e.g., `email.mime.text`).
        parent : Package
            Graph node for the package providing this module *or* `None` if
            this module is a top-level module.

        Returns
        ----------
        Node
            Graph node created for this module.
        """
        # If this module has a graph hook, run that hook first.
        if fqname in self._graph_hooks:
            hook_filename = self._graph_hooks[fqname]
            logger.info('Processing graph hook   %s', os.path.basename(hook_filename))
            hook_namespace = importlib_load_source('pyi_graph_hook.' + fqname, hook_filename)

            # Graph hooks are required to define the hook() function.
            if not hasattr(hook_namespace, 'hook'):
                raise NameError('hook() function undefined in graph hook "%s".' % hook_filename)

            # Pass this hook the current module graph.
            hook_namespace.hook(self)

            # Prevent the next import of this module from rerunning this hook
            del self._graph_hooks[fqname]

        return super(PyiModuleGraph, self)._import_module(
            partname, fqname, parent)

    def get_code_objects(self):
        """
        Get code objects from ModuleGraph for pure Pyhton modules. This allows
        to avoid writing .pyc/pyo files to hdd at later stage.

        :return: Dict with module name and code object.
        """
        code_dict = {}
        mod_types = set(['Module', 'SourceModule', 'CompiledModule', 'Package'])
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

    def make_a_TOC(self, typecode=None, existing_TOC=None):
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
        # Construct regular expression for matching modules that should be
        # excluded because they are bundled in base_library.zip.
        regex_str = '|'.join(['(%s.*)' % x for x in PY3_BASE_MODULES])
        module_filter = re.compile(regex_str)

        result = existing_TOC or TOC()
        for node in self.flatten(start=self._top_script_node):
            # TODO This is terrible. Everything in Python has a type. It's
            # nonsensical to even speak of "nodes [that] are not typed." How
            # would that even occur? After all, even "None" has a type! (It's
            # "NoneType", for the curious.) Remove this, please.

            # Skip modules that are in base_library.zip.
            if not is_py2 and module_filter.match(node.identifier):
                continue

            # get node type e.g. Script
            mg_type = type(node).__name__
            assert mg_type is not None
            # translate to the corresponding TOC typecode, or leave as-is
            toc_type = self.typedict.get(mg_type, mg_type)
            if typecode and not (toc_type in typecode):
                # Type is not a to be selected one, skip this one
                continue
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

    def importer_names(self, name):
        """
        List the names of all modules importing the module with the passed name.

        If this module has yet to be imported and hence added to the graph, this
        method returns the empty list; else, this method returns a list
        comprehension over the identifiers of all graph nodes having an outgoing
        edge directed into the graph node for this module.

        Parameters
        ----------
        name : str
            Fully-qualified name of the module to be examined.

        Returns
        ----------
        list
            List of the fully-qualified names of all modules importing the
            module with the passed fully-qualified name.
        """
        node = self.findNode(name)
        if node is None : return []
        _, iter_inc = self.get_edges(node)
        return [importer.identifier for importer in iter_inc]


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
        temp_toc = self.make_a_TOC(['EXTENSION', 'PYMODULE', 'PYSOURCE'])
        for (mod_name, path, typecode) in temp_toc:
            # Look if there is any run-time hook for given module.
            if mod_name in self._available_rthooks:
                # There could be several run-time hooks for a module.
                for hook in self._available_rthooks[mod_name]:
                    logger.info("Including run-time hook %r", hook)
                    path = os.path.join(self._homepath, 'PyInstaller', 'loader', 'rthooks', hook)
                    rthooks_nodes.append(self.run_script(path))

        return rthooks_nodes

    def add_hiddenimports(self, module_list):
        """
        Add hidden imports that are either supplied as CLI option --hidden-import=MODULENAME
        or as dependencies from some PyInstaller features when enabled (e.g. crypto feature).
        """
        # Analyze the script's hidden imports (named on the command line)
        for modnm in module_list:
            logger.debug('Hidden import: %s' % modnm)
            if self.findNode(modnm) is not None:
                logger.debug('Hidden import %r already found', modnm)
                continue
            logger.info("Analyzing hidden import %r", modnm)
            # ModuleGraph throws ImportError if import not found
            try :
                node = self.import_hook(modnm)
            except ImportError:
                logger.error("Hidden import %r not found", modnm)


    def get_co_using_ctypes(self):
        """
        Find modules that imports Python module 'ctypes'.

        Modules that imports 'ctypes' probably load a dll that might be required
        for bundling with the executable. The usual way to load a DLL is using:
            ctypes.CDLL('libname')
            ctypes.cdll.LoadLibrary('libname')

        :return: Code objects that might be scanned for module dependencies.
        """
        co_dict = {}
        node = self.findNode('ctypes')
        if node:
            referers = self.getReferers(node)
            for r in referers:
                co_dict[r.identifier] = r.code
        return co_dict


def initialize_modgraph():
    """
    Create module dependency graph and for Python 3 analyze dependencies
    for base_library.zip. These are same for every executable.

    :return: PyiModuleGraph object with basic dependencies.
    """
    logger.info('Initializing module dependency graph...')
    graph = PyiModuleGraph(HOMEPATH, implies=get_implies(), debug=0)

    if not is_py2:
        logger.info('Analyzing base_library.zip ...')
        required_mods = []
        # Collect submodules from required modules in base_library.zip.
        for m in PY3_BASE_MODULES:
            if is_package(m):
                required_mods += collect_submodules(m)
            else:
                required_mods.append(m)
        # Initialize ModuleGraph.
        for m in required_mods:
            graph.import_hook(m)
    return graph


def get_bootstrap_modules():
    """
    Get TOC with the bootstrapping modules and their dependencies.
    :return: TOC with modules
    """
    # Import 'struct' modules to get real paths to module file names.
    mod_struct = __import__('struct')
    # Basic modules necessary for the bootstrap process.
    loader_mods = []
    loaderpath = os.path.join(HOMEPATH, 'PyInstaller', 'loader')
    # On some platforms (Windows, Debian/Ubuntu) '_struct' and zlib modules are
    # built-in modules (linked statically) and thus does not have attribute __file__.
    # 'struct' module is required for reading Python bytecode from executable.
    # 'zlib' is required to decompress this bytecode.
    for mod_name in ['_struct', 'zlib']:
        mod = __import__(mod_name)  # C extension.
        if hasattr(mod, '__file__'):
            loader_mods.append(('_struct', os.path.abspath(mod.__file__), 'EXTENSION'))
    # NOTE:These modules should be kept simple without any complicated dependencies.
    loader_mods +=[
        ('struct', os.path.abspath(mod_struct.__file__), 'PYMODULE'),
        ('pyimod01_os_path', os.path.join(loaderpath, 'pyimod01_os_path.pyc'), 'PYMODULE'),
        ('pyimod02_archive',  os.path.join(loaderpath, 'pyimod02_archive.pyc'), 'PYMODULE'),
        ('pyimod03_importers',  os.path.join(loaderpath, 'pyimod03_importers.pyc'), 'PYMODULE'),
        ('pyiboot01_bootstrap', os.path.join(loaderpath, 'pyiboot01_bootstrap.py'), 'PYSOURCE'),
        ('pyiboot02_egg_install', os.path.join(loaderpath, 'pyiboot02_egg_install.py'), 'PYSOURCE'),
    ]
    # TODO Why is here the call to TOC()?
    toc = TOC(loader_mods)
    return toc.data
