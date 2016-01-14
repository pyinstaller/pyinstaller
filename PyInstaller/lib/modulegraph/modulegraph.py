"""
Find modules used by a script, using bytecode analysis.

Based on the stdlib modulefinder by Thomas Heller and Just van Rossum,
but uses a graph data structure and 2.3 features

XXX: Verify all calls to import_hook (and variants) to ensure that
imports are done in the right way.
"""
from __future__ import absolute_import, print_function

import pkg_resources

import dis
import imp
import marshal
import os
import pkgutil
import sys
import struct
import re
from collections import deque, namedtuple
import ast
import zipfile

from ..altgraph.ObjectGraph import ObjectGraph
from ..altgraph import GraphError

from . import util
from . import zipio

if sys.version_info[0] == 2:
    from StringIO import StringIO as BytesIO
    from StringIO import StringIO
    from  urllib import pathname2url
    def _Bchr(value):
        return chr(value)

else:
    from urllib.request  import pathname2url
    from io import BytesIO, StringIO

    def _Bchr(value):
        return value


# File open mode for reading (univeral newlines)
if sys.version_info[0] == 2:
    _READ_MODE = "rU"
else:
    _READ_MODE = "r"

# TODO: Refactor all uses of explicit filetypes in this module *AND* of the
# imp.get_suffixes() function to use this dictionary instead. Unfortunately,
# tests for explicit filetypes (e.g., ".py") are non-portable. Under Windows,
# for example, both the ".py" *AND* ".pyw" filetypes signify valid uncompiled
# Python modules.
# TODO: The imp.get_suffixes() function (in fact, the entire "imp" package) has
# been deprecated as of Python 3.3 by the importlib.machinery.all_suffixes()
# function, which largely performs the same role. Unfortunately, the latter
# function was only introduced with Python 3.3. Since PyInstaller requires
# Python >= 3.3 when running under Python 3, refactor this as follows:
#
# * Under Python 2, continue calling imp.get_suffixes().
# * Under Python 3, call importlib.machinery.all_suffixes() instead.
_IMPORTABLE_FILETYPE_TO_METADATA = {
    filetype: (filetype, open_mode, imp_type)
    for filetype, open_mode, imp_type in imp.get_suffixes()
}
"""
Dictionary mapping the filetypes of importable files to the 3-tuple of metadata
describing such files returned by the `imp.get_suffixes()` function whose first
element is that filetype.

This dictionary simplifies platform-portable importation of importable files,
including:

* Uncompiled modules suffixed by `.py` (as well as `.pyw` under Windows).
* Compiled modules suffixed by either `.pyc` or `.pyo`.
* C extensions suffixed by the platform-specific shared library filetype (e.g.,
  `.so` under Linux, `.dll` under Windows).

The keys of this dictionary are `.`-prefixed filetypes (e.g., `.py`, `.so');
the values of this dictionary are 3-tuples whose:

1. First element is the same `.`-prefixed filetype.
1. Second element is the mode to be passed to the `open()` built-in to open
   files of that filetype under the current platform and Python interpreter
   (e.g., `rU` for the `.py` filetype under Python 2, `r` for the same
   filetype under Python 3).
1. Third element is a magic number specific to the `imp` module (e.g.,
   `imp.C_EXTENSION` for filetypes corresponding to C extensions).
"""



# Modulegraph does a good job at simulating Python's, but it can not
# handle packagepath modifications packages make at runtime.  Therefore there
# is a mechanism whereby you can register extra paths in this map for a
# package, and it will be honored.
#
# Note this is a mapping is lists of paths.
_packagePathMap = {}

# Prefix used in magic .pth files used by setuptools to create namespace
# packages without an __init__.py file.
#
# The value is a list of such prefixes as the prefix varies with versions of
# setuptools.
_SETUPTOOLS_NAMESPACEPKG_PTHs=(
    "import sys,types,os; p = os.path.join(sys._getframe(1).f_locals['sitedir'], *('",
    "import sys,new,os; p = os.path.join(sys._getframe(1).f_locals['sitedir'], *('",
    "import sys, types, os;p = os.path.join(sys._getframe(1).f_locals['sitedir'], *('",
)


def _namespace_package_path(fqname, pathnames, path=None):
    """
    Return the __path__ for the python package in *fqname*.

    This function uses setuptools metadata to extract information
    about namespace packages from installed eggs.
    """
    working_set = pkg_resources.WorkingSet(path)

    path = list(pathnames)

    for dist in working_set:
        if dist.has_metadata('namespace_packages.txt'):
            namespaces = dist.get_metadata(
                    'namespace_packages.txt').splitlines()
            if fqname in namespaces:
                nspath = os.path.join(dist.location, *fqname.split('.'))
                if nspath not in path:
                    path.append(nspath)

    return path

_strs = re.compile(r'''^\s*["']([A-Za-z0-9_]+)["'],?\s*''') # "<- emacs happy

def _eval_str_tuple(value):
    """
    Input is the repr of a tuple of strings, output
    is that tuple.

    This only works with a tuple where the members are
    python identifiers.
    """
    if not (value.startswith('(') and value.endswith(')')):
        raise ValueError(value)

    orig_value = value
    value = value[1:-1]

    result = []
    while value:
        m = _strs.match(value)
        if m is None:
            raise ValueError(orig_value)

        result.append(m.group(1))
        value = value[len(m.group(0)):]

    return tuple(result)

def _path_from_importerror(exc, default):
    # This is a hack, but sadly enough the necessary information
    # isn't available otherwise.
    m = re.match('^No module named (\S+)$', str(exc))
    if m is not None:
        return m.group(1)

    return default

def os_listdir(path):
    """
    Deprecated name
    """
    warnings.warn("Use zipio.listdir instead of os_listdir",
            DeprecationWarning)
    return zipio.listdir(path)


def _code_to_file(co):
    """ Convert code object to a .pyc pseudo-file """
    return BytesIO(
            imp.get_magic() + b'\0\0\0\0' + marshal.dumps(co))

def moduleInfoForPath(path):
    for (ext, readmode, typ) in imp.get_suffixes():
        if path.endswith(ext):
            return os.path.basename(path)[:-len(ext)], readmode, typ
    return None

# A Public interface
import warnings
def AddPackagePath(packagename, path):
    warnings.warn("Use addPackagePath instead of AddPackagePath",
            DeprecationWarning)

    addPackagePath(packagename, path)

def addPackagePath(packagename, path):
    paths = _packagePathMap.get(packagename, [])
    paths.append(path)
    _packagePathMap[packagename] = paths

_replacePackageMap = {}

# This ReplacePackage mechanism allows modulefinder to work around the
# way the _xmlplus package injects itself under the name "xml" into
# sys.modules at runtime by calling ReplacePackage("_xmlplus", "xml")
# before running ModuleGraph.
def ReplacePackage(oldname, newname):
    warnings.warn("use replacePackage instead of ReplacePackage",
            DeprecationWarning)
    replacePackage(oldname, newname)

def replacePackage(oldname, newname):
    _replacePackageMap[oldname] = newname


class DependencyInfo (namedtuple("DependencyInfo", ["conditional", "function", "tryexcept", "fromlist"])):
    __slots__ = ()

    def _merged(self, other):
        if (not self.conditional and not self.function and not self.tryexcept) \
                or (not other.conditional and not other.function and not other.tryexcept):
            return DependencyInfo(conditional=False, function=False, tryexcept=False, fromlist=self.fromlist and other.fromlist)

        else:
            return DependencyInfo(
                    conditional=self.conditional or other.conditional,
                    function=self.function or other.function,
                    tryexcept=self.tryexcept or other.tryexcept,
                    fromlist=self.fromlist and other.fromlist)


class Node(object):
    def __init__(self, identifier):
        self.debug = 0
        self.graphident = identifier
        self.identifier = identifier
        self._namespace = {}
        self.filename = None
        self.packagepath = None
        self.code = None
        # The set of global names that are assigned to in the module.
        # This includes those names imported through starimports of
        # Python modules.
        # These are only relevant when looking up the from-list in
        # `from xxx import yyy`, since `import xxx.yyy` requires `yyy`
        # to be a module and thus the globalnames need not to be
        # checked.
        self.globalnames = set()
        # The set of starimports this module did that could not be
        # resolved, ie. a starimport from a non-Python module.
        self.starimports = set()

    def __contains__(self, name):
        return name in self._namespace

    def __getitem__(self, name):
        return self._namespace[name]

    def __setitem__(self, name, value):
        self._namespace[name] = value

    def get(self, *args):
        return self._namespace.get(*args)

    def __cmp__(self, other):
        try:
            otherIdent = getattr(other, 'graphident')
        except AttributeError:
            return NotImplemented

        return cmp(self.graphident, otherIdent)

    def __eq__(self, other):
        try:
            otherIdent = getattr(other, 'graphident')
        except AttributeError:
            return False

        return self.graphident == otherIdent

    def __ne__(self, other):
        try:
            otherIdent = getattr(other, 'graphident')
        except AttributeError:
            return True

        return self.graphident != otherIdent

    def __lt__(self, other):
        try:
            otherIdent = getattr(other, 'graphident')
        except AttributeError:
            return NotImplemented

        return self.graphident < otherIdent

    def __le__(self, other):
        try:
            otherIdent = getattr(other, 'graphident')
        except AttributeError:
            return NotImplemented

        return self.graphident <= otherIdent

    def __gt__(self, other):
        try:
            otherIdent = getattr(other, 'graphident')
        except AttributeError:
            return NotImplemented

        return self.graphident > otherIdent

    def __ge__(self, other):
        try:
            otherIdent = getattr(other, 'graphident')
        except AttributeError:
            return NotImplemented

        return self.graphident >= otherIdent


    def __hash__(self):
        return hash(self.graphident)

    def infoTuple(self):
        return (self.identifier,)

    def __repr__(self):
        return '%s%r' % (type(self).__name__, self.infoTuple())

class Alias(str):
    pass

class AliasNode(Node):
    def __init__(self, name, node):
        super(AliasNode, self).__init__(name)
        for k in 'identifier', 'packagepath', '_namespace', 'globalnames', 'starimports':
            setattr(self, k, getattr(node, k, None))

    def infoTuple(self):
        return (self.graphident, self.identifier)

class BadModule(Node):
    pass

class ExcludedModule(BadModule):
    pass

class MissingModule(BadModule):
    pass

class Script(Node):
    def __init__(self, filename):
        super(Script, self).__init__(filename)
        self.filename = filename

    def infoTuple(self):
        return (self.filename,)

class BaseModule(Node):
    def __init__(self, name, filename=None, path=None):
        super(BaseModule, self).__init__(name)
        self.filename = filename
        self.packagepath = path

    def infoTuple(self):
        return tuple(filter(None, (self.identifier, self.filename, self.packagepath)))

class BuiltinModule(BaseModule):
    pass

class RuntimeModule(MissingModule):
    """
    Graph node representing a Python module dynamically defined at runtime.

    Most modules are statically defined at creation time in external Python
    files. Some modules, however, are dynamically defined at runtime (e.g.,
    `six.moves`, dynamically defined by the statically defined `six` module).

    This node represents such a module. To ensure that the parent module of
    this module is also imported and added to the graph, this node is typically
    added to the graph by calling the `ModuleGraph.add_module()` method.
    """
    pass

class SourceModule(BaseModule):
    pass

class InvalidSourceModule(SourceModule):
    pass

class CompiledModule(BaseModule):
    pass

class InvalidCompiledModule(BaseModule):
    pass

class Package(BaseModule):
    pass

class NamespacePackage(Package):
    pass

class Extension(BaseModule):
    pass

class FlatPackage(BaseModule): # nocoverage
    def __init__(self, *args, **kwds):
        warnings.warn("This class will be removed in a future version of modulegraph",
            DeprecationWarning)
        super(FlatPackage, *args, **kwds)

class ArchiveModule(BaseModule): # nocoverage
    def __init__(self, *args, **kwds):
        warnings.warn("This class will be removed in a future version of modulegraph",
            DeprecationWarning)
        super(FlatPackage, *args, **kwds)

# HTML templates for ModuleGraph generator
header = """\
<html>
  <head>
    <title>%(TITLE)s</title>
    <style>
      .node { margin:1em 0; }
    </style>
  </head>
  <body>
    <h1>%(TITLE)s</h1>"""
entry = """
<div class="node">
  <a name="%(NAME)s" />
  %(CONTENT)s
</div>"""
contpl = """<tt>%(NAME)s</tt> %(TYPE)s"""
contpl_linked = """\
<a target="code" href="%(URL)s" type="text/plain"><tt>%(NAME)s</tt></a>"""
imports = """\
  <div class="import">
%(HEAD)s:
  %(LINKS)s
  </div>
"""
footer = """
  </body>
</html>"""

def _ast_names(names):
    result = []
    for nm in names:
        if isinstance(nm, ast.alias):
            result.append(nm.name)
        else:
            result.append(nm)

    result = [r for r in result if r != '__main__']
    return result


if sys.version_info[0] == 2:
    DEFAULT_IMPORT_LEVEL= -1
else:
    DEFAULT_IMPORT_LEVEL= 0

class _Visitor (ast.NodeVisitor):
    def __init__(self, graph, module):
        self._graph = graph
        self._module = module
        # Importing a module twice *may* happen, e.g. with
        # replacePackage or `_xmlplus` as `xml`
        #assert module._imported_modules is None, module
        module._imported_modules = []
        self._level = DEFAULT_IMPORT_LEVEL
        self._in_if = [False]
        self._in_def = [False]
        self._in_tryexcept = [False]

    @property
    def in_if(self):
        return self._in_if[-1]

    @property
    def in_def(self):
        return self._in_def[-1]

    @property
    def in_tryexcept(self):
        return self._in_tryexcept[-1]

    def _collect_import(self, name, fromlist, level):

        if sys.version_info[0] == 2:
            if name == '__future__' and 'absolute_import' in (fromlist or ()):
                self._level = 0

        have_star = False
        if fromlist is not None:
            fromlist = set(fromlist)
            if '*' in fromlist:
                fromlist.remove('*')
                have_star = True

        # Collect this import to belong to this module
        self._module._imported_modules.append(
            (have_star,
             (name, self._module, fromlist, level),
             {'attr': DependencyInfo(
                 conditional=self.in_if,
                 tryexcept=self.in_tryexcept,
                 function=self.in_def,
                 fromlist=False)}))

    def visit_Import(self, node):
        for nm in _ast_names(node.names):
            self._collect_import(nm, None, self._level)

    def visit_ImportFrom(self, node):
        level = node.level if node.level != 0 else self._level
        self._collect_import(node.module or '', _ast_names(node.names), level)

    def visit_If(self, node):
        self._in_if.append(True)
        self.generic_visit(node)
        self._in_if.pop()

    def visit_FunctionDef(self, node):
        self._in_def.append(True)
        self.generic_visit(node)
        self._in_def.pop()

    def visit_Try(self, node):
        self._in_tryexcept.append(True)
        self.generic_visit(node)
        self._in_tryexcept.pop()

    def visit_ExceptHandler(self, node):
        self._in_tryexcept.append(True)
        self.generic_visit(node)
        self._in_tryexcept.pop()

    def visit_TryExcept(self, node):
        self._in_tryexcept.append(True)
        self.generic_visit(node)
        self._in_tryexcept.pop()

    def visit_ExceptHandler(self, node):
        self._in_tryexcept.append(True)
        self.generic_visit(node)
        self._in_tryexcept.pop()

    def visit_Expression(self, node):
        # Expression node's cannot contain import statements or
        # other nodes that are relevant for us.
        pass

    # Expression isn't actually used as such in AST trees,
    # therefore define visitors for all kinds of expression nodes.
    visit_BoolOp = visit_Expression
    visit_BinOp = visit_Expression
    visit_UnaryOp = visit_Expression
    visit_Lambda = visit_Expression
    visit_IfExp = visit_Expression
    visit_Dict = visit_Expression
    visit_Set = visit_Expression
    visit_ListComp = visit_Expression
    visit_SetComp = visit_Expression
    visit_ListComp = visit_Expression
    visit_GeneratorExp = visit_Expression
    visit_Compare = visit_Expression
    visit_Yield = visit_Expression
    visit_YieldFrom = visit_Expression
    visit_Await = visit_Expression
    visit_Call = visit_Expression



class ModuleGraph(ObjectGraph):
    """
    Directed graph whose nodes represent modules and edges represent
    dependencies between these modules.
    """

    def createNode(self, cls, name, *args, **kw):
        m = self.findNode(name)
        if m is None:
            #assert m is None, m
            m = super(ModuleGraph, self).createNode(cls, name, *args, **kw)
            m._imported_modules = None
        return m

    def __init__(self, path=None, excludes=(), replace_paths=(), implies=(), graph=None, debug=0):
        super(ModuleGraph, self).__init__(graph=graph, debug=debug)
        if path is None:
            path = sys.path
        self.path = path
        self.lazynodes = {}
        # excludes is stronger than implies
        self.lazynodes.update(dict(implies))
        for m in excludes:
            self.lazynodes[m] = None
        self.replace_paths = replace_paths

        self.nspackages = self._calc_setuptools_nspackages()
        # Maintain own list of package path mappings in the scope of Modulegraph
        # object.
        self._package_path_map = _packagePathMap

    def _calc_setuptools_nspackages(self):
        # Setuptools has some magic handling for namespace
        # packages when using 'install --single-version-externally-managed'
        # (used by system packagers and also by pip)
        #
        # When this option is used namespace packages are writting to
        # disk *without* an __init__.py file, which means the regular
        # import machinery will not find them.
        #
        # We therefore explicitly look for the hack used by
        # setuptools to get this kind of namespace packages to work.

        pkgmap = {}

        try:
            from pkgutil import ImpImporter
        except ImportError:
            try:
                from _pkgutil import ImpImporter
            except ImportError:
                ImpImporter = pkg_resources.ImpWrapper

        if sys.version_info[:2] >= (3,3):
            import importlib.machinery
            ImpImporter = importlib.machinery.FileFinder

        for entry in self.path:
            importer = pkg_resources.get_importer(entry)

            if isinstance(importer, ImpImporter):
                try:
                    ldir = os.listdir(entry)
                except os.error:
                    continue

                for fn in ldir:
                    if fn.endswith('-nspkg.pth'):
                        fp = open(os.path.join(entry, fn), 'rU')
                        try:
                            for ln in fp:
                                for pfx in _SETUPTOOLS_NAMESPACEPKG_PTHs:
                                    if ln.startswith(pfx):
                                        try:
                                            start = len(pfx)-2
                                            stop = ln.index(')', start)+1
                                        except ValueError:
                                            continue

                                        pkg = _eval_str_tuple(ln[start:stop])
                                        identifier = ".".join(pkg)
                                        subdir = os.path.join(entry, *pkg)
                                        if os.path.exists(os.path.join(subdir, '__init__.py')):
                                            # There is a real __init__.py, ignore the setuptools hack
                                            continue

                                        if identifier in pkgmap:
                                            pkgmap[identifier].append(subdir)
                                        else:
                                            pkgmap[identifier] = [subdir]
                                        break
                        finally:
                            fp.close()

        return pkgmap

    def implyNodeReference(self, node, other, edge_data=None):
        """
        Create a reference from the passed source node to the passed other node,
        implying the former to depend upon the latter.

        While the source node *must* be an existing graph node, the target node
        may be either an existing graph node *or* a fully-qualified module name.
        In the latter case, the module with that name and all parent packages of
        that module will be imported *without* raising exceptions and for each
        newly imported module or package:

        * A new graph node will be created for that module or package.
        * A reference from the passed source node to that module or package will
          be created.

        This method allows dependencies between Python objects *not* importable
        with standard techniques (e.g., module aliases, C extensions).

        Parameters
        ----------
        node : str
            Graph node for this reference's source module or package.
        other : {Node, str}
            Either a graph node *or* fully-qualified name for this reference's
            target module or package.
        """
        if isinstance(other, Node):
            self._updateReference(node, other, edge_data)

        else:
            if isinstance(other, tuple):
                raise ValueError(other)

            others = self._safe_import_hook(other, node, None)
            for other in others:
                self._updateReference(node, other, edge_data)


    def getReferences(self, fromnode):
        """
        Yield all nodes that 'fromnode' dependes on (that is,
        all modules that 'fromnode' imports.
        """
        node = self.findNode(fromnode)
        out_edges, _ = self.get_edges(node)
        return out_edges

    def getReferers(self, tonode, collapse_missing_modules=True):
        node = self.findNode(tonode)
        _, in_edges = self.get_edges(node)

        if collapse_missing_modules:
            for n in in_edges:
                if isinstance(n, MissingModule):
                    for n in self.getReferers(n, False):
                        yield n

                else:
                    yield n

        else:
            for n in in_edges:
                yield n

    def hasEdge(self, fromnode, tonode):
        """ Return True iff there is an edge from 'fromnode' to 'tonode' """
        fromnode = self.findNode(fromnode)
        tonode = self.findNode(tonode)

        return self.graph.edge_by_node(fromnode, tonode) is not None


    def foldReferences(self, packagenode):
        """
        Create edges to/from 'packagenode' based on the
        edges to/from modules in package. The module nodes
        are then hidden.
        """
        pkg = self.findNode(packagenode)

        for n in self.nodes():
            if not n.identifier.startswith(pkg.identifier + '.'):
                continue

            iter_out, iter_inc = n.get_edges()
            for other in iter_out:
                if other.identifier.startswith(pkg.identifier + '.'):
                    continue

                if not self.hasEdge(pkg, other):
                    # Ignore circular dependencies
                    self._updateReference(pkg, other, 'pkg-internal-import')

            for other in iter_in:
                if other.identifier.startswith(pkg.identifier + '.'):
                    # Ignore circular dependencies
                    continue

                if not self.hasEdge(other, pkg):
                    self._updateReference(other, pkg, 'pkg-import')

            self.graph.hide_node(n)

    # TODO: unfoldReferences(pkg) that restore the submodule nodes and
    #       removes 'pkg-import' and 'pkg-internal-import' edges. Care should
    #       be taken to ensure that references are correct if multiple packages
    #       are folded and then one of them in unfolded


    def _updateReference(self, fromnode, tonode, edge_data):
        try:
            ed = self.edgeData(fromnode, tonode)
        except (KeyError, GraphError): # XXX: Why 'GraphError'
            return self.createReference(fromnode, tonode, edge_data)

        if not (isinstance(ed, DependencyInfo) and isinstance(edge_data, DependencyInfo)):
            self.updateEdgeData(fromnode, tonode, edge_data)
        else:
            self.updateEdgeData(fromnode, tonode, ed._merged(edge_data))


    def createReference(self, fromnode, tonode, edge_data='direct'):
        """
        Create a reference from fromnode to tonode
        """
        return super(ModuleGraph, self).createReference(fromnode, tonode, edge_data=edge_data)

    def findNode(self, name, create_nspkg=True):
        """
        Find a node by identifier.  If a node by that identifier exists,
        it will be returned.

        If a lazy node exists by that identifier with no dependencies (excluded),
        it will be instantiated and returned.

        If a lazy node exists by that identifier with dependencies, it and its
        dependencies will be instantiated and scanned for additional dependencies.

        If a namespace package exists by that identifier, it will be instantiated
        and returned.

        If `create_nspkg` is False, no namespace package will be instantiated.
        """
        data = super(ModuleGraph, self).findNode(name)
        if data is not None:
            return data
        if name in self.lazynodes:
            deps = self.lazynodes.pop(name)
            if deps is None:
                # excluded module
                m = self.createNode(ExcludedModule, name)
            elif isinstance(deps, Alias):
                other = self._safe_import_hook(deps, None, None).pop()
                m = self.createNode(AliasNode, name, other)
                self.implyNodeReference(m, other)

            else:
                m = self._safe_import_hook(name, None, None).pop()
                for dep in deps:
                    self.implyNodeReference(m, dep)
            return m

        if name in self.nspackages and create_nspkg:
            # name is a --single-version-externally-managed
            # namespace package (setuptools/distribute)
            pathnames = self.nspackages.pop(name)
            m = self.createNode(NamespacePackage, name)

            # FIXME: The filename must be set to a string to ensure that py2app
            # works, it is not clear yet why that is. Setting to None would be
            # cleaner.
            m.filename = '-'
            m.packagepath = _namespace_package_path(name, pathnames, self.path)

            # As per comment at top of file, simulate runtime packagepath additions.
            m.packagepath = m.packagepath + self._package_path_map.get(name, [])
            return m

        return None

    def run_script(self, pathname, caller=None):
        """
        Create a node by path (not module name).  It is expected to be a Python
        source file, and will be scanned for dependencies.
        """
        self.msg(2, "run_script", pathname)
        pathname = os.path.realpath(pathname)
        m = self.findNode(pathname)
        if m is not None:
            return m

        if sys.version_info[0] != 2:
            with open(pathname, 'rb') as fp:
                encoding = util.guess_encoding(fp)

            with open(pathname, _READ_MODE, encoding=encoding) as fp:
                contents = fp.read() + '\n'

        else:
            with open(pathname, _READ_MODE) as fp:
                contents = fp.read() + '\n'

        co_ast = compile(contents, pathname, 'exec', ast.PyCF_ONLY_AST, True)
        co = compile(co_ast, pathname, 'exec', 0, True)
        m = self.createNode(Script, pathname)
        self._updateReference(caller, m, None)
        self._scan_code(m, co, co_ast)
        m.code = co
        if self.replace_paths:
            m.code = self._replace_paths_in_code(m.code)
        return m

    def import_hook(self, name, caller=None, fromlist=None, level=DEFAULT_IMPORT_LEVEL, attr=None):
        """
        Import a module

        Return the set of modules that are imported
        """
        self.msg(3, "import_hook", name, caller, fromlist, level)
        parent = self._determine_parent(caller)
        q, tail = self._find_head_package(parent, name, level)
        m = self._load_tail(q, tail)
        modules = [m]
        if fromlist and m.packagepath:
            for s in self._ensure_fromlist(m, fromlist):
                if s not in modules:
                    modules.append(s)
        for m in modules:
            self._updateReference(caller, m, edge_data=attr)
        return modules

    def _determine_parent(self, caller):
        """
        Determine the package containing a node
        """
        self.msgin(4, "determine_parent", caller)
        parent = None
        if caller:
            pname = caller.identifier

            if isinstance(caller, Package):
                parent = caller

            elif '.' in pname:
                pname = pname[:pname.rfind('.')]
                parent = self.findNode(pname)

            elif caller.packagepath:
                # XXX: I have no idea why this line
                # is necessary.
                parent = self.findNode(pname)


        self.msgout(4, "determine_parent ->", parent)
        return parent

    def _find_head_package(self, parent, name, level=DEFAULT_IMPORT_LEVEL):
        """
        Given a calling parent package and an import name determine the containing
        package for the name
        """
        self.msgin(4, "find_head_package", parent, name, level)
        if '.' in name:
            head, tail = name.split('.', 1)
        else:
            head, tail = name, ''

        if level == -1:
            if parent:
                qname = parent.identifier + '.' + head
            else:
                qname = head

        elif level == 0:
            qname = head

            # Absolute import, ignore the parent
            parent = None

        else:
            if parent is None:
                self.msg(2, "Relative import outside of package")
                raise ImportError("Relative import outside of package (name=%r, parent=%r, level=%r)"%(name, parent, level))

            for i in range(level-1):
                if '.' not in parent.identifier:
                    self.msg(2, "Relative import outside of package")
                    raise ImportError("Relative import outside of package (name=%r, parent=%r, level=%r)"%(name, parent, level))

                p_fqdn = parent.identifier.rsplit('.', 1)[0]
                new_parent = self.findNode(p_fqdn)
                if new_parent is None:
                    self.msg(2, "Relative import outside of package")
                    raise ImportError("Relative import outside of package (name=%r, parent=%r, level=%r)"%(name, parent, level))

                assert new_parent is not parent, (new_parent, parent)
                parent = new_parent

            if head:
                qname = parent.identifier + '.' + head
            else:
                qname = parent.identifier


        q = self._safe_import_module(head, qname, parent)
        if q:
            self.msgout(4, "find_head_package ->", (q, tail))
            return q, tail
        if parent:
            qname = head
            parent = None
            q = self._safe_import_module(head, qname, parent)
            if q:
                self.msgout(4, "find_head_package ->", (q, tail))
                return q, tail
        self.msgout(4, "raise ImportError: No module named", qname)
        raise ImportError("No module named " + qname)

    def _load_tail(self, mod, tail):
        self.msgin(4, "load_tail", mod, tail)
        result = mod
        while tail:
            i = tail.find('.')
            if i < 0: i = len(tail)
            head, tail = tail[:i], tail[i+1:]
            mname = "%s.%s" % (result.identifier, head)
            result = self._safe_import_module(head, mname, result)
            if result is None:
                # result = self.createNode(MissingModule, mname)
                self.msgout(4, "raise ImportError: No module named", mname)
                raise ImportError("No module named " + repr(mname))
        self.msgout(4, "load_tail ->", result)
        return result

    def _ensure_fromlist(self, m, fromlist):
        fromlist = set(fromlist)
        self.msg(4, "ensure_fromlist", m, fromlist)
        if '*' in fromlist:
            fromlist.update(self._find_all_submodules(m))
            fromlist.remove('*')
        for sub in fromlist:
            submod = m.get(sub)
            if submod is None:
                if sub in m.globalnames:
                    # Name is a global in the module
                    self.msg(4, 'Global name found:', m.identifier, sub)
                    continue
                # XXX: ^^^ need something simular for names imported
                #      by 'm'.

                fullname = m.identifier + '.' + sub
                submod = self._safe_import_module(sub, fullname, m)
                if submod is None:
                    raise ImportError("No module named " + fullname)
            yield submod

    def _find_all_submodules(self, m):
        if not m.packagepath:
            return
        # 'suffixes' used to be a list hardcoded to [".py", ".pyc", ".pyo"].
        # But we must also collect Python extension modules - although
        # we cannot separate normal dlls from Python extensions.
        suffixes = [triple[0] for triple in imp.get_suffixes()]
        for path in m.packagepath:
            try:
                names = zipio.listdir(path)
            except (os.error, IOError):
                self.msg(2, "can't list directory", path)
                continue
            for info in (moduleInfoForPath(p) for p in names):
                if info is None: continue
                if info[0] != '__init__':
                    yield info[0]

    def alias_module(self, src_module_name, trg_module_name):
        """
        Alias the source module to the target module with the passed names.

        This method ensures that the next call to findNode() given the target
        module name will resolve this alias. This includes importing and adding
        a graph node for the source module if needed as well as adding a
        reference from the target to source module.

        Parameters
        ----------
        src_module_name : str
            Fully-qualified name of the existing **source module** (i.e., the
            module being aliased).
        trg_module_name : str
            Fully-qualified name of the non-existent **target module** (i.e.,
            the alias to be created).
        """
        self.msg(3, 'alias_module "%s" -> "%s"' % (src_module_name, trg_module_name))
        # print('alias_module "%s" -> "%s"' % (src_module_name, trg_module_name))
        assert isinstance(src_module_name, str), '"%s" not a module name.' % str(src_module_name)
        assert isinstance(trg_module_name, str), '"%s" not a module name.' % str(trg_module_name)

        # If the target module has already been added to the graph as either a
        # non-alias or as a different alias, raise an exception.
        trg_module = self.findNode(trg_module_name)
        if trg_module is not None and not (
           isinstance(trg_module, AliasNode) and
           trg_module.identifier == src_module_name):
            raise ValueError('Target module "%s" already imported as "%s".' % (trg_module_name, trg_module))

        # See findNode() for details.
        self.lazynodes[trg_module_name] = Alias(src_module_name)

    def add_module(self, module):
        """
        Add the passed module node to the graph if not already added.

        If that module has a parent module or package with a previously added
        node, this method also adds a reference from this module node to its
        parent node and adds this module node to its parent node's namespace.

        This high-level method wraps the low-level `addNode()` method, but is
        typically *only* called by graph hooks adding runtime module nodes. For
        all other node types, the `import_module()` method should be called.

        Parameters
        ----------
        module : BaseModule
            Graph node for the module to be added.
        """
        self.msg(3, 'import_module_runtime', module)

        # If no node exists for this module, add such a node.
        module_added = self.findNode(module.identifier)
        if module_added is None:
            self.addNode(module)
        else:
            assert module == module_added, 'Newly added module "%s" != previously added module "%s".' % (str(module), str(module_added))

        # If this module has a previously added parent, reference this module to
        # its parent and add this module to its parent's namespace.
        parent_name, _, module_basename = module.identifier.rpartition('.')
        if parent_name:
            parent = self.findNode(parent_name)
            if parent is None:
                self.msg(4, 'import_module_runtime parent not found:', parent_name)
            else:
                self.createReference(module, parent)
                parent[module_basename] = module

    def append_package_path(self, package_name, directory):
        """
        Modulegraph does a good job at simulating Python's, but it can not
        handle packagepath __path__ modifications packages make at runtime.
        Therefore there is a mechanism whereby you can register extra paths
        in this map for a package, and it will be honored.

        NOTE: This method has to be called before a package is resolved by
              modulegraph.

        :param module: fully qualified module name
        :param directory: directory to append to the  __path__ attribute.
        """
        paths = self._package_path_map.setdefault(package_name, [])
        paths.append(directory)


    def _safe_import_module(
        self, module_basename, module_name, parent_package):
        """
        Create a new graph node for the module with the passed name under the
        parent package signified by the passed graph node _without_ raising
        `ImportError` exceptions.

        If this module has already been imported, this module's existing graph
        node will be returned; else if this module is importable, a new graph
        node will be added for this module and returned; else this module is
        unimportable, in which case `None` will be returned. Like the
        `_safe_import_hook()` method, this method does _not_ raise
        `ImportError` exceptions when this module is unimportable.

        Parameters
        ----------
        module_basename : str
            Unqualified name of the module to be imported (e.g., `text`).
        module_name : str
            Fully-qualified name of this module (e.g., `email.mime.text`).
        parent_package : Package
            Graph node for the previously imported package containing this
            module _or_ `None` if this module is a **top-level module** (i.e.,
            `fqname` contains no `.` delimiters).

        Returns
        ----------
        Node
            Graph node created for this module or `None` if this module is
            unimportable.
        """
        self.msgin(3, "safe_import_module", module_basename, module_name, parent_package)
        module = self.findNode(module_name)

        # If this module has *NOT* already been imported, do so.
        if module is None:
            # List of the absolute paths of all directories to be searched for
            # this module. This effectively defaults to "sys.path".
            search_dirs = None

            # Open file handle providing the physical contents of this module.
            file_handle = None

            # If this module has a parent package...
            if parent_package is not None:
                # ...with a list of the absolute paths of all directories
                # comprising this package, prefer that to "sys.path".
                if parent_package.packagepath is not None:
                    search_dirs = parent_package.packagepath
                # Else, something is horribly wrong. Return emptiness.
                else:
                    self.msgout(3, "safe_import_module -> None (parent_parent.packagepath is None)")
                    return None

            try:
                try:
                    file_handle, pathname, metadata = self._find_module(
                        module_basename, search_dirs, parent_package)
                except ImportError as exc:
                    self.msgout(3, "safe_import_module -> None (%r)" % exc)
                    return None

                module = self._load_module(
                    module_name, file_handle, pathname, metadata)
            finally:
                if file_handle is not None:
                    file_handle.close()

        # If this module has a parent package, add an edge from the former to
        # the latter regardless of whether this module has already been
        # imported or not.
        if parent_package is not None:
            self.msg(4, "safe_import_module create reference", module, "->", parent_package)
            self._updateReference(
                module, parent_package, edge_data=DependencyInfo(
                    conditional=False,
                    fromlist=False,
                    function=False,
                    tryexcept=False,
            ))
            parent_package[module_basename] = module

        self.msgout(3, "safe_import_module ->", module)
        return module

    def _load_module(self, fqname, fp, pathname, info):
        suffix, mode, typ = info
        self.msgin(2, "load_module", fqname, fp and "fp", pathname)

        if typ == imp.PKG_DIRECTORY:
            if isinstance(mode, (list, tuple)):
                packagepath = mode
            else:
                packagepath = []

            m = self._load_package(fqname, pathname, packagepath)
            self.msgout(2, "load_module ->", m)
            return m

        if typ == imp.PY_SOURCE:
            contents = fp.read()
            if isinstance(contents, bytes):
                contents += b'\n'
            else:
                contents += '\n'

            try:
                co = compile(contents, pathname, 'exec', ast.PyCF_ONLY_AST, True)
                #co = compile(contents, pathname, 'exec', 0, True)
            except SyntaxError:
                co = None
                cls = InvalidSourceModule

            else:
                cls = SourceModule

        elif typ == imp.PY_COMPILED:
            if fp.read(4) != imp.get_magic():
                self.msg(2, "load_module: InvalidCompiledModule", pathname)
                co = None
                cls = InvalidCompiledModule

            else:
                fp.read(4)
                try:
                    co = marshal.loads(fp.read())
                    cls = CompiledModule
                except Exception:
                    co = None
                    cls = InvalidCompiledModule

        elif typ == imp.C_BUILTIN:
            cls = BuiltinModule
            co = None

        else:
            cls = Extension
            co = None

        m = self.createNode(cls, fqname)
        m.filename = pathname
        if co is not None:
            if isinstance(co, ast.AST):
                co_ast = co
                co = compile(co_ast, pathname, 'exec', 0, True)
            else:
                co_ast = None
            self._scan_code(m, co, co_ast)

            if self.replace_paths:
                co = self._replace_paths_in_code(co)
            m.code = co

        self.msgout(2, "load_module ->", m)
        return m

    def _safe_import_hook(self, name, caller, fromlist, level=DEFAULT_IMPORT_LEVEL, attr=None):
        # wrapper for self.import_hook() that won't raise ImportError

        # List of graph nodes created for the modules imported by this call.
        mods = None

        # True if this is a Python 2-style implicit relative import of a
        # SWIG-generated C extension.
        is_swig_import = False

        # Attempt to import the module with Python's standard module importers.
        try:
            mods = self.import_hook(name, caller, level=level, attr=attr)
        # Failing that, defer to custom module importers handling non-standard
        # import schemes (e.g., SWIG, six).
        except ImportError as msg:
            # If this is an absolute top-level import under Python 3 and if the
            # name to be imported is the caller's name prefixed by "_", this
            # could be a SWIG-generated Python 2-style implicit relative import.
            # SWIG-generated files contain functions named swig_import_helper()
            # importing dynamic libraries residing in the same directory. For
            # example, a SWIG-generated caller module "csr.py" might resemble:
            #
            #     # This file was automatically generated by SWIG (http://www.swig.org).
            #     ...
            #     def swig_import_helper():
            #         ...
            #         try:
            #             fp, pathname, description = imp.find_module('_csr', [dirname(__file__)])
            #         except ImportError:
            #             import _csr
            #             return _csr
            #
            # While there exists no reasonable means for modulegraph to parse
            # the call to imp.find_module(), the subsequent implicit relative
            # import is trivially parsable. This import is prohibited under
            # Python 3, however, and thus parsed only if the caller's file is
            # parsable plaintext (as indicated by a filetype of ".py") and the
            # first line of this file is the above SWIG header comment.
            #
            # The constraint that this library's name be the caller's name
            # prefixed by '_' is explicitly mandated by SWIG and thus a
            # reliable indicator of "SWIG-ness". The SWIG documentation states:
            # "When linking the module, the name of the output file has to match
            #  the name of the module prefixed by an underscore."
            #
            # A MissingModule is not a SWIG import candidate.
            if caller is not None and type(caller) is not MissingModule and \
                            fromlist is None and level == 0 and \
                            caller.filename.endswith('.py') and \
                            name == '_' + caller.identifier.rpartition('.')[2] and \
                            sys.version_info[0] == 3:
                self.msg(4, 'SWIG import candidate (name=%r, caller=%r, level=%r)' % (name, caller, level))

                # TODO Define a new function util.open_text_file() performing
                # this logic, which is repeated numerous times in this module.
                with open(caller.filename, 'rb') as caller_file:
                    encoding = util.guess_encoding(caller_file)
                with open(caller.filename, _READ_MODE, encoding=encoding) as caller_file:
                    first_line = caller_file.readline()
                    self.msg(5, 'SWIG import candidate shebang: %r' % (first_line))
                    if "automatically generated by SWIG" in first_line:
                        is_swig_import = True

                        # Convert this Python 2-style implicit relative import
                        # into a Python 3-style explicit relative import for
                        # the duration of this function call by overwriting
                        # the original parameters passed to this call.
                        fromlist = [name]
                        name = ''
                        level = 1
                        self.msg(2, 'SWIG import (caller=%r, fromlist=%r, level=%r)' % (caller, fromlist, level))

                        # Import the caller module importing this library.
                        try:
                            mods = self.import_hook(
                                name, caller, level=level, attr=attr)
                        except ImportError as msg:
                            self.msg(2, "SWIG ImportError:", str(msg))

            # If this module remains unimportable, add a MissingModule node.
            if mods is None:
                self.msg(2, "ImportError:", str(msg))

                m = self.createNode(MissingModule, _path_from_importerror(msg, name))
                self._updateReference(caller, m, edge_data=attr)

        # If this module was successfully imported, get its graph node.
        if mods is not None:
            assert len(mods) == 1, 'Expected import_hook() to return only one module but received: %r' % str(mods)
            m = list(mods)[0]

        subs = [m]
        if isinstance(attr, DependencyInfo):
            attr = attr._replace(fromlist=True)
        for sub in (fromlist or ()):
            # If this name is in the module namespace already,
            # then add the entry to the list of substitutions
            if sub in m:
                sm = m[sub]
                if sm is not None:
                    if sm not in subs:
                        self._updateReference(caller, sm, edge_data=attr)
                        subs.append(sm)
                    continue

            elif sub in m.globalnames:
                # Global variable in the module, ignore
                self.msg(4, 'Global name found:', m.identifier, sub)
                continue


            # See if we can load it
            #    fullname = name + '.' + sub
            fullname = m.identifier + '.' + sub
            #else:
            #    print("XXX", repr(name), repr(sub), repr(caller), repr(m))
            sm = self.findNode(fullname)
            if sm is None:
                try:
                    sm = self.import_hook(name, caller, fromlist=[sub], level=level, attr=attr)
                except ImportError as msg:
                    self.msg(2, "ImportError:", str(msg))
                    #sm = self.createNode(MissingModule, _path_from_importerror(msg, fullname))
                    sm = self.createNode(MissingModule, fullname)
                else:
                    sm = self.findNode(fullname)
                    if sm is None:
                        sm = self.createNode(MissingModule, fullname)

                    # If this is a SWIG C extension, instruct downstream
                    # freezers (py2app, PyInstaller) to freeze this extension
                    # under its unqualified rather than qualified name (e.g.,
                    # as "_csr" rather than "scipy.sparse.sparsetools._csr"),
                    # permitting the implicit relative import in its parent
                    # SWIG module to successfully find this extension.
                    if is_swig_import:
                        # If a graph node with that name already exists, avoid
                        # collisions by emitting an error instead.
                        if self.findNode(sub):
                            self.msg(2, 'SWIG import error: %r basename %r already exists' % (fullname, sub))
                        else:
                            self.msg(4, 'SWIG import renamed from %r to %r' % (fullname, sub))
                            sm.identifier = sub

            m[sub] = sm
            if sm is not None:
                self._updateReference(m, sm, edge_data=attr)
                self._updateReference(caller, sm, edge_data=attr)
                if sm not in subs:
                    subs.append(sm)
        return subs

    def _scan_code(self, m, co, co_ast=None):
        if co_ast is not None:
            self._scan_ast(co_ast, m)
            self._scan_bytecode_stores(co, m)
        else:
            m._imported_modules = []
            self._scan_bytecode(co, m)

        # Actually import the modules collected while scanning.
        # We need to suspend the globalnames as otherwise
        # `_safe_import_hook()` would take identfiers imported via
        # `from . import abc` as existing global names and not try to
        # import them. Please note: This only effects this form of
        # import where relative_module is "." For all other cases, the
        # imported module is already processed and all global names
        # are in place anyway.
        globalnames = m.globalnames
        m.globalnames = set()
        self._process_imports(m)
        m.globalnames = globalnames


    def _scan_ast(self, co, m):
        visitor = _Visitor(self, m)
        visitor.visit(co)

    def _scan_bytecode_stores(self, co, m,
            STORE_NAME=_Bchr(dis.opname.index('STORE_NAME')),
            STORE_GLOBAL=_Bchr(dis.opname.index('STORE_GLOBAL')),
            HAVE_ARGUMENT=_Bchr(dis.HAVE_ARGUMENT),
            unpack=struct.unpack):

        extended_import = bool(sys.version_info[:2] >= (2,5))

        code = co.co_code
        constants = co.co_consts
        n = len(code)
        i = 0

        while i < n:
            c = code[i]
            i += 1
            if c >= HAVE_ARGUMENT:
                i = i+2

            if c == STORE_NAME or c == STORE_GLOBAL:
                # keep track of all global names that are assigned to
                oparg = unpack('<H', code[i - 2:i])[0]
                name = co.co_names[oparg]
                m.globalnames.add(name)

        cotype = type(co)
        for c in constants:
            if isinstance(c, cotype):
                self._scan_bytecode_stores(c, m)

    def _scan_bytecode(self, co, m,
            HAVE_ARGUMENT=_Bchr(dis.HAVE_ARGUMENT),
            LOAD_CONST=_Bchr(dis.opname.index('LOAD_CONST')),
            IMPORT_NAME=_Bchr(dis.opname.index('IMPORT_NAME')),
            IMPORT_FROM=_Bchr(dis.opname.index('IMPORT_FROM')),
            STORE_NAME=_Bchr(dis.opname.index('STORE_NAME')),
            STORE_GLOBAL=_Bchr(dis.opname.index('STORE_GLOBAL')),
            unpack=struct.unpack):

        # Python >=2.5: LOAD_CONST flags, LOAD_CONST names, IMPORT_NAME name
        # Python < 2.5: LOAD_CONST names, IMPORT_NAME name
        extended_import = bool(sys.version_info[:2] >= (2,5))

        code = co.co_code
        constants = co.co_consts
        n = len(code)
        i = 0

        level = None
        fromlist = None

        while i < n:
            c = code[i]
            i += 1
            if c >= HAVE_ARGUMENT:
                i = i+2

            if c == IMPORT_NAME:
                if extended_import:
                    assert code[i-9] == LOAD_CONST
                    assert code[i-6] == LOAD_CONST
                    arg1, arg2 = unpack('<xHxH', code[i-9:i-3])
                    level = co.co_consts[arg1]
                    fromlist = co.co_consts[arg2]
                else:
                    assert code[-6] == LOAD_CONST
                    arg1, = unpack('<xH', code[i-6:i-3])
                    level = -1
                    fromlist = co.co_consts[arg1]

                assert fromlist is None or type(fromlist) is tuple
                oparg, = unpack('<H', code[i - 2:i])
                name = co.co_names[oparg]
                have_star = False
                if fromlist is not None:
                    fromlist = set(fromlist)
                    if '*' in fromlist:
                        fromlist.remove('*')
                        have_star = True

                # Collect this import to belong to this module
                m._imported_modules.append((have_star,
                                            (name, m, fromlist, level),
                                            {}))

            elif c == STORE_NAME or c == STORE_GLOBAL:
                # keep track of all global names that are assigned to
                oparg = unpack('<H', code[i - 2:i])[0]
                name = co.co_names[oparg]
                m.globalnames.add(name)

        cotype = type(co)
        for c in constants:
            if isinstance(c, cotype):
                self._scan_bytecode(c, m)


    def _process_imports(self, m):
        """
        Actally import the modules collected in _scan_code (resp.
        _scan_ast, _scan_bytecode, and _scan_bytecode_stores).
        """
        if m._imported_modules is None:
            return
        for have_star, import_info, kwargs in m._imported_modules:
            imported_module = self._safe_import_hook(*import_info, **kwargs)[0]

            if have_star:
                m.globalnames.update(imported_module.globalnames)
                m.starimports.update(imported_module.starimports)
                if imported_module.code is None:
                    name = import_info[0]
                    m.starimports.add(name)


    def _load_package(self, fqname, pathname, pkgpath):
        """
        Called only when an imp.PKG_DIRECTORY is found
        """
        self.msgin(2, "load_package", fqname, pathname, pkgpath)
        newname = _replacePackageMap.get(fqname)
        if newname:
            fqname = newname

        ns_pkgpath = _namespace_package_path(fqname, pkgpath or [], self.path)
        if ns_pkgpath or pkgpath:
            # this is a namespace package
            m = self.createNode(NamespacePackage, fqname)
            m.filename = '-'
            m.packagepath = ns_pkgpath
        else:
            m = self.createNode(Package, fqname)
            m.filename = pathname
            # PEP-302-compliant loaders return the pathname of the
            # `__init__`-file, not the packge directory.
            if os.path.basename(pathname).startswith('__init__.'):
                pathname = os.path.dirname(pathname)
            m.packagepath = [pathname] + ns_pkgpath

        # As per comment at top of file, simulate runtime packagepath additions.
        m.packagepath = m.packagepath + self._package_path_map.get(fqname, [])

        try:
            self.msg(2, "find __init__ for %s"%(m.packagepath,))
            fp, buf, stuff = self._find_module("__init__", m.packagepath, parent=m)
        except ImportError:
            pass

        else:
            try:
                self.msg(2, "load __init__ for %s"%(m.packagepath,))
                self._load_module(fqname, fp, buf, stuff)
            finally:
                if fp is not None:
                    fp.close()
        self.msgout(2, "load_package ->", m)
        return m

    def _find_module(self, name, path, parent=None):
        """
        Get a 3-tuple detailing the physical location of the Python module with
        the passed name if that module is found *or* raise `ImportError`
        otherwise.

        This high-level method wraps the low-level `modulegraph.find_module()`
        function with additional support for graph-based module caching.

        Parameters
        ----------
        name : str
            Fully-qualified name of the Python module to be found.
        path : list
            List of the absolute paths of all directories to search for this
            module *or* `None` if the default path list `self.path` is to be
            searched.
        parent : Node
            Optional parent module of this module if this module is a submodule
            of another module *or* `None` if this module is a top-level module.

        Returns
        ----------
        (file_handle, filename, metadata)
            See `modulegraph._find_module()` for details.
        """
        if parent is not None:
            # assert path is not None
            fullname = parent.identifier + '.' + name
        else:
            fullname = name

        node = self.findNode(fullname)
        if node is not None:
            self.msg(3, "find_module: already included?", node)
            raise ImportError(name)

        if path is None:
            if name in sys.builtin_module_names:
                return (None, None, ("", "", imp.C_BUILTIN))

            path = self.path

        return self._find_module_path(fullname, name, path)

    def _find_module_path(self, fullname, module_name, search_dirs):
        """
        Get a 3-tuple detailing the physical location of the module with the
        passed name if that module exists _or_ raise `ImportError` otherwise.

        This low-level function is a variant on the standard `imp.find_module()`
        function with additional support for:

        * Multiple search paths. The passed list of absolute paths will be
          iteratively searched for the first directory containing a file
          corresponding to this module.
        * Compressed (e.g., zipped) packages.

        For efficiency, the higher level `ModuleGraph._find_module()` method
        wraps this function with support for module caching.

        Parameters
        ----------
        module_name : str
            Fully-qualified name of the module to be found.
        search_dirs : list
            List of the absolute paths of all directories to search for this
            module (in order). Searching will halt at the first directory
            containing this module.

        Returns
        ----------
        (file_handle, filename, metadata)
            3-tuple describing the physical location of this module, where:
            * `file_handle` is an open read-only file handle from which the
              on-disk contents of this module may be read if this is a
              pure-Python module or `None` otherwise (e.g., if this is a
              package or C extension).
            * `filename` is the absolute path of this file.
            * `metadata` is itself a 3-tuple `(filetype, open_mode, imp_type)`.
              See the `_IMPORTABLE_FILETYPE_TO_METADATA` dictionary for
              details.

        Raises
        ----------
        ImportError
            If this module is _not_ found.
        """
        self.msgin(4, "_find_module_path <-", fullname, search_dirs)

        # TODO: Under:
        #
        # * Python 3.3, the following logic should be replaced by logic
        #   leveraging only the "importlib" module.
        # * Python 3.4, the following logic should be replaced by a call to
        #   importlib.util.find_spec().

        # Top-level 3-tuple to be returned.
        path_data = None

        # File handle to be returned.
        file_handle = None

        # List of the absolute paths of all directories comprising the
        # namespace package to which this module belongs if any.
        namespace_dirs = []

        try:
            for search_dir in search_dirs:
                # PEP 302-compliant importer making loaders for this directory.
                importer = pkgutil.get_importer(search_dir)

                # If this directory is not importable, continue.
                if importer is None:
                    # self.msg(4, "_find_module_path importer not found", search_dir)
                    continue

                # Get the PEP 302-compliant loader object loading this module.
                #
                # If this importer defines the PEP 302-compliant find_loader()
                # method, prefer that.
                if hasattr(importer, 'find_loader'):
                    loader, loader_namespace_dirs = importer.find_loader(
                        module_name)
                    namespace_dirs.extend(loader_namespace_dirs)
                # Else if this importer defines the Python 2-specific
                # find_module() method, fall back to that. Despite the method
                # name, this method returns a loader rather than a module.
                elif hasattr(importer, 'find_module'):
                    loader = importer.find_module(module_name)
                # Else, raise an exception.
                else:
                    raise ImportError(
                        "Module %r importer %r loader unobtainable" % (module_name, importer))

                # If this module is not loadable from this directory, continue.
                if loader is None:
                    # self.msg(4, "_find_module_path loader not found", search_dir)
                    continue

                # 3-tuple of metadata to be returned.
                metadata = None

                # Absolute path of this module. If this module resides in a
                # compressed archive, this is the absolute path of this module
                # after extracting this module from that archive and hence
                # should not exist; else, this path should typically exist.
                pathname = None

                # If this loader defines the PEP 302-compliant get_filename()
                # method, preferably call that method first. Most if not all
                # loaders (including zipimporter objects) define this method.
                if hasattr(loader, 'get_filename'):
                    pathname = loader.get_filename(module_name)
                # Else if this loader provides a "path" attribute, defer to that.
                elif hasattr(loader, 'path'):
                    pathname = loader.path
                # Else, raise an exception.
                else:
                    raise ImportError(
                        "Module %r loader %r path unobtainable" % (module_name, loader))

                # If no path was found, this is probably a namespace package. In
                # such case, continue collecting namespace directories.
                if pathname is None:
                    self.msg(4, "_find_module_path path not found", pathname)
                    continue

                # If this loader defines the PEP 302-compliant is_package()
                # method returning True, this is a non-namespace package.
                if hasattr(loader, 'is_package') and loader.is_package(module_name):
                    metadata = ('', '', imp.PKG_DIRECTORY)
                # Else, this is either a module or C extension.
                else:
                    # In either case, this path must have a filetype.
                    filetype = os.path.splitext(pathname)[1]
                    if not filetype:
                        raise ImportError(
                            'Non-package module %r path %r has no filetype' % (module_name, pathname))

                    # 3-tuple of metadata specific to this filetype.
                    metadata = _IMPORTABLE_FILETYPE_TO_METADATA.get(
                        filetype, None)
                    if metadata is None:
                        raise ImportError(
                            'Non-package module %r filetype %r unrecognized' % (pathname, filetype))

                    # See "_IMPORTABLE_FILETYPE_TO_METADATA" for details.
                    open_mode = metadata[1]
                    imp_type = metadata[2]

                    # If this is a C extension, leave this path unopened.
                    if imp_type == imp.C_EXTENSION:
                        pass
                    # Else, this is a module.
                    #
                    # If this loader defines the PEP 302-compliant get_source()
                    # method, open the returned string as a file-like buffer.
                    elif imp_type == imp.PY_SOURCE and hasattr(loader, 'get_source'):
                        file_handle = StringIO(loader.get_source(module_name))
                    # If this loader defines the PEP 302-compliant get_code()
                    # method, open the returned object as a file-like buffer.
                    elif imp_type == imp.PY_COMPILED and hasattr(loader, 'get_code'):
                        try:
                            code_object = loader.get_code(module_name)
                            if code_object is None:
                                file_handle = BytesIO(b'\0\0\0\0\0\0\0\0')
                            else:
                                file_handle = _code_to_file(code_object)
                        except ImportError:
                            # post-bone the ImportError until load_module
                            file_handle = BytesIO(b'\0\0\0\0\0\0\0\0')
                    # If this is an uncompiled file under Python 3, open this
                    # file for encoding-aware text reading.
                    elif imp_type == imp.PY_SOURCE and sys.version_info[0] == 3:
                        with open(pathname, 'rb') as file_handle:
                            encoding = util.guess_encoding(file_handle)
                        file_handle = open(
                            pathname, open_mode, encoding=encoding)
                    # Else, this is either a compiled file or an uncompiled
                    # file under Python 2. In either case, open this file.
                    else:
                        file_handle = open(pathname, open_mode)

                # Return such metadata.
                path_data = (file_handle, pathname, metadata)
                break
            # Else if this is a namespace package, return such metadata.
            else:
                if namespace_dirs:
                    path_data = (None, namespace_dirs[0], (
                        '', namespace_dirs, imp.PKG_DIRECTORY))
        # Ensure that exceptions are logged, as this function is typically
        # called by the import_module() method which squelches ImportErrors.
        except Exception as exc:
            self.msgout(4, "_find_module_path -> exception", exc)
            raise

        # If this module was not found, raise an exception.
        self.msgout(4, "_find_module_path ->", path_data)
        if path_data is None:
            raise ImportError("No module named " + repr(module_name))

        return path_data


    def create_xref(self, out=None):
        global header, footer, entry, contpl, contpl_linked, imports
        if out is None:
            out = sys.stdout
        scripts = []
        mods = []
        for mod in self.flatten():
            name = os.path.basename(mod.identifier)
            if isinstance(mod, Script):
                scripts.append((name, mod))
            else:
                mods.append((name, mod))
        scripts.sort()
        mods.sort()
        scriptnames = [name for name, m in scripts]
        scripts.extend(mods)
        mods = scripts

        title = "modulegraph cross reference for "  + ', '.join(scriptnames)
        print(header % {"TITLE": title}, file=out)

        def sorted_namelist(mods):
            lst = [os.path.basename(mod.identifier) for mod in mods if mod]
            lst.sort()
            return lst
        for name, m in mods:
            content = ""
            if isinstance(m, BuiltinModule):
                content = contpl % {"NAME": name,
                                    "TYPE": "<i>(builtin module)</i>"}
            elif isinstance(m, Extension):
                content = contpl % {"NAME": name,\
                                    "TYPE": "<tt>%s</tt>" % m.filename}
            else:
                url = pathname2url(m.filename or "")
                content = contpl_linked % {"NAME": name, "URL": url}
            oute, ince = map(sorted_namelist, self.get_edges(m))
            if oute:
                links = ""
                for n in oute:
                    links += """  <a href="#%s">%s</a>\n""" % (n, n)
                content += imports % {"HEAD": "imports", "LINKS": links}
            if ince:
                links = ""
                for n in ince:
                    links += """  <a href="#%s">%s</a>\n""" % (n, n)
                content += imports % {"HEAD": "imported by", "LINKS": links}
            print(entry % {"NAME": name,"CONTENT": content}, file=out)
        print(footer, file=out)


    def itergraphreport(self, name='G', flatpackages=()):
        # XXX: Can this be implemented using Dot()?
        nodes = list(map(self.graph.describe_node, self.graph.iterdfs(self)))
        describe_edge = self.graph.describe_edge
        edges = deque()
        packagenodes = set()
        packageidents = {}
        nodetoident = {}
        inpackages = {}
        mainedges = set()

        # XXX - implement
        flatpackages = dict(flatpackages)

        def nodevisitor(node, data, outgoing, incoming):
            if not isinstance(data, Node):
                return {'label': str(node)}
            #if isinstance(d, (ExcludedModule, MissingModule, BadModule)):
            #    return None
            s = '<f0> ' + type(data).__name__
            for i,v in enumerate(data.infoTuple()[:1], 1):
                s += '| <f%d> %s' % (i,v)
            return {'label':s, 'shape':'record'}


        def edgevisitor(edge, data, head, tail):
            # XXX: This method nonsense, the edge
            # data is never initialized.
            if data == 'orphan':
                return {'style':'dashed'}
            elif data == 'pkgref':
                return {'style':'dotted'}
            return {}

        yield 'digraph %s {\n' % (name,)
        attr = dict(rankdir='LR', concentrate='true')
        cpatt  = '%s="%s"'
        for item in attr.items():
            yield '\t%s;\n' % (cpatt % item,)

        # find all packages (subgraphs)
        for (node, data, outgoing, incoming) in nodes:
            nodetoident[node] = getattr(data, 'identifier', None)
            if isinstance(data, Package):
                packageidents[data.identifier] = node
                inpackages[node] = set([node])
                packagenodes.add(node)


        # create sets for subgraph, write out descriptions
        for (node, data, outgoing, incoming) in nodes:
            # update edges
            for edge in (describe_edge(e) for e in outgoing):
                edges.append(edge)

            # describe node
            yield '\t"%s" [%s];\n' % (
                node,
                ','.join([
                    (cpatt % item) for item in
                    nodevisitor(node, data, outgoing, incoming).items()
                ]),
            )

            inside = inpackages.get(node)
            if inside is None:
                inside = inpackages[node] = set()
            ident = nodetoident[node]
            if ident is None:
                continue
            pkgnode = packageidents.get(ident[:ident.rfind('.')])
            if pkgnode is not None:
                inside.add(pkgnode)


        graph = []
        subgraphs = {}
        for key in packagenodes:
            subgraphs[key] = []

        while edges:
            edge, data, head, tail = edges.popleft()
            if ((head, tail)) in mainedges:
                continue
            mainedges.add((head, tail))
            tailpkgs = inpackages[tail]
            common = inpackages[head] & tailpkgs
            if not common and tailpkgs:
                usepkgs = sorted(tailpkgs)
                if len(usepkgs) != 1 or usepkgs[0] != tail:
                    edges.append((edge, data, head, usepkgs[0]))
                    edges.append((edge, 'pkgref', usepkgs[-1], tail))
                    continue
            if common:
                common = common.pop()
                if tail == common:
                    edges.append((edge, data, tail, head))
                elif head == common:
                    subgraphs[common].append((edge, 'pkgref', head, tail))
                else:
                    edges.append((edge, data, common, head))
                    edges.append((edge, data, common, tail))

            else:
                graph.append((edge, data, head, tail))

        def do_graph(edges, tabs):
            edgestr = tabs + '"%s" -> "%s" [%s];\n'
            # describe edge
            for (edge, data, head, tail) in edges:
                attribs = edgevisitor(edge, data, head, tail)
                yield edgestr % (
                    head,
                    tail,
                    ','.join([(cpatt % item) for item in attribs.items()]),
                )

        for g, edges in subgraphs.items():
            yield '\tsubgraph "cluster_%s" {\n' % (g,)
            yield '\t\tlabel="%s";\n' % (nodetoident[g],)
            for s in do_graph(edges, '\t\t'):
                yield s
            yield '\t}\n'

        for s in do_graph(graph, '\t'):
            yield s

        yield '}\n'


    def graphreport(self, fileobj=None, flatpackages=()):
        if fileobj is None:
            fileobj = sys.stdout
        fileobj.writelines(self.itergraphreport(flatpackages=flatpackages))

    def report(self):
        """Print a report to stdout, listing the found modules with their
        paths, as well as modules that are missing, or seem to be missing.
        """
        print()
        print("%-15s %-25s %s" % ("Class", "Name", "File"))
        print("%-15s %-25s %s" % ("-----", "----", "----"))
        # Print modules found
        sorted = [(os.path.basename(mod.identifier), mod) for mod in self.flatten()]
        sorted.sort()
        for (name, m) in sorted:
            print("%-15s %-25s %s" % (type(m).__name__, name, m.filename or ""))

    def _replace_paths_in_code(self, co):
        new_filename = original_filename = os.path.normpath(co.co_filename)
        for f, r in self.replace_paths:
            f = os.path.join(f, '')
            r = os.path.join(r, '')
            if original_filename.startswith(f):
                new_filename = r + original_filename[len(f):]
                break

        else:
            return co

        consts = list(co.co_consts)
        for i in range(len(consts)):
            if isinstance(consts[i], type(co)):
                consts[i] = self._replace_paths_in_code(consts[i])

        code_func = type(co)

        if hasattr(co, 'co_kwonlyargcount'):
            return code_func(co.co_argcount, co.co_kwonlyargcount, co.co_nlocals, co.co_stacksize,
                         co.co_flags, co.co_code, tuple(consts), co.co_names,
                         co.co_varnames, new_filename, co.co_name,
                         co.co_firstlineno, co.co_lnotab,
                         co.co_freevars, co.co_cellvars)
        else:
            return code_func(co.co_argcount, co.co_nlocals, co.co_stacksize,
                         co.co_flags, co.co_code, tuple(consts), co.co_names,
                         co.co_varnames, new_filename, co.co_name,
                         co.co_firstlineno, co.co_lnotab,
                         co.co_freevars, co.co_cellvars)
