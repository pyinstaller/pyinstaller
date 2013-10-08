#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
All we're doing here is tracking, not importing
If we were importing, these would be hooked to the real module objects
"""


import ctypes
import os

from PyInstaller.compat import PYCO
# TODO Remove ctypes imports and scan_code.
#from PyInstaller.depend.utils import _resolveCtypesImports, scan_code

import PyInstaller.depend.impdirector
import PyInstaller.utils.misc


class Module:
    _ispkg = 0
    typ = 'UNKNOWN'

    def __init__(self, nm):
        self.__name__ = nm
        self.__file__ = None
        self._all = []
        self.imports = []
        self.warnings = []
        self.binaries = []
        self.datas = []
        self._xref = {}

    def ispackage(self):
        return self._ispkg

    def doimport(self, nm):
        pass

    def xref(self, nm):
        self._xref[nm] = 1

    def __str__(self):
        return ("<%s %r %s imports=%s binaries=%s datas=%s>" %
                (self.__class__.__name__, self.__name__, self.__file__,
                 self.imports, self.binaries, self.datas))


class BuiltinModule(Module):
    typ = 'BUILTIN'

    def __init__(self, nm):
        Module.__init__(self, nm)


class ExtensionModule(Module):
    typ = 'EXTENSION'

    def __init__(self, nm, pth):
        Module.__init__(self, nm)
        self.__file__ = pth


class PyModule(Module):
    typ = 'PYMODULE'

    def __init__(self, nm, pth, co):
        Module.__init__(self, nm)
        self.co = co
        self.__file__ = pth
        if os.path.splitext(self.__file__)[1] == '.py':
            self.__file__ = self.__file__ + PYCO
        self.scancode()

    def _remove_duplicate_entries(self, item_list):
        """
        Remove duplicate entries from the list.
        """
        # The strategy is to convert a list to a set and then back.
        # This conversion will eliminate duplicate entries.
        return list(set(item_list))

    def scancode(self):
        self.imports, self.warnings, self.binaries, allnms = scan_code(self.co)
        # TODO There has to be some bugs in the 'scan_code()' functions because
        #      some imports are present twice in the self.imports list.
        #      This could be fixed when scan_code will be replaced by package
        #      modulegraph.
        self.imports = self._remove_duplicate_entries(self.imports)

        if allnms:
            self._all = allnms
        if ctypes and self.binaries:
            self.binaries = _resolveCtypesImports(self.binaries)
            # Just to make sure there will be no duplicate entries.
            self.binaries = self._remove_duplicate_entries(self.binaries)


class PyScript(PyModule):
    typ = 'PYSOURCE'

    def __init__(self, pth, co):
        Module.__init__(self, '__main__')
        self.co = co
        self.__file__ = pth
        self.scancode()


class PkgModule(PyModule):
    typ = 'PYMODULE'

    def __init__(self, nm, pth, co):
        PyModule.__init__(self, nm, pth, co)
        self._ispkg = 1
        pth = os.path.dirname(pth)
        self.__path__ = [pth]
        self._update_director(force=True)

    def _update_director(self, force=False):
        if force or self.subimporter.path != self.__path__:
            self.subimporter = PyInstaller.depend.impdirector.PathImportDirector(self.__path__)

    def doimport(self, nm):
        self._update_director()
        mod = self.subimporter.getmod(nm)
        if mod:
            mod.__name__ = self.__name__ + '.' + mod.__name__
        return mod


class PkgInPYZModule(PyModule):
    def __init__(self, nm, co, pyzowner):
        PyModule.__init__(self, nm, co.co_filename, co)
        self._ispkg = 1
        self.__path__ = [str(pyzowner)]
        self.owner = pyzowner

    def doimport(self, nm):
        mod = self.owner.getmod(self.__name__ + '.' + nm)
        return mod


class PyInZipModule(PyModule):
    typ = 'ZIPFILE'

    def __init__(self, zipowner, nm, pth, co):
        PyModule.__init__(self, nm, co.co_filename, co)
        self.owner = zipowner


class PkgInZipModule(PyModule):
    typ = 'ZIPFILE'

    def __init__(self, zipowner, nm, pth, co):
        PyModule.__init__(self, nm, co.co_filename, co)
        self._ispkg = 1
        self.__path__ = [str(zipowner)]
        self.owner = zipowner

    def doimport(self, nm):
        mod = self.owner.getmod(self.__name__ + '.' + nm)
        return mod


# ----------------------------------------------------------------
'''
Create a "mod": an object with info about an imported module.
This is the historic API object passed to the hook(mod) method
of a hook-modname.py file. Originally a mod object was created
by the old ImpTracker, and was similar to a modulegraph node, although
with more data. Hooks relied on the following properties:
     mod.__file__ for the full path to a script
   * mod.__path__ for the full path to a package or module
   * mod.co for the compiled code of a script or module
   * mod.datas for a list of associated data files
   * mod.imports for a list of things this module imports
   * mod.binaries for a list of (name,path,'BINARY') tuples (or a TOC)
 (* means, the hook might modify this member)
The new mod provides these members for examination only but has
methods for modification:
   mod.add_binary( (name, path, typecode) ) add a binary dependency
   mod.add_import( modname ) add a python import
   mod.del_import( modname ) remove a python dependency
   mod.retarget( path, code ) retarget to a different piece of code (hook-site)
The mod object is just used for communication with hooks.
It is constructed before the call from modulegraph info.
Afterward, changes are returned to the graph and other dicts.
'''
# TODO: move this to depend.module and replace Module with it

class FakeModule(Module):
    def __init__(self, identifier, graph) :
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
        if not isinstance(names, list):
            names = [names]  # Allow passing string or list.
        self._added_imports.extend(names) # save change to implement in graph later
        for name in names:
            self.imports.append([name,1,0,-1]) # make change visible to caller

    def del_import(self,names):
        # just save to implement in graph later
        if not isinstance(names, list):
            names = [names]  # Allow passing string or list.
        self._deleted_imports.extend(names)

    def add_binary(self,list_of_tuples):
        self._added_binaries.append(list_of_tuples)
        self.binaries.append(list_of_tuples)
    
    def retarget(self, path_to_new_code):
        # Used by hook-site (and others?) to retarget a module to a simpler one
        # more suited to being frozen. 
        
        # Keep the original filename in the fake code object.
        new_code = PyInstaller.utils.misc.get_code_object(path_to_new_code, new_filename=self.node.filename)
        # Update node.
        self.node.code = new_code
        self.node.filename = path_to_new_code
        # Update dependencies in the graph.
        self.graph.scan_code(new_code, self.node)
        
# ----------------------------------------------------------------
# End FakeModule
# ----------------------------------------------------------------
