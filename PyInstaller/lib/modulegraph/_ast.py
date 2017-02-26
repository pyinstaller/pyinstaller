import ast
import sys
import codecs
import imp

from collections import namedtuple

BOM = codecs.BOM_UTF8.decode('utf-8')

#FIXME: Leverage this rather than magic numbers below.
ABSOLUTE_OR_RELATIVE_IMPORT_LEVEL = -1
"""
Constant instructing the builtin `__import__()` function to attempt both
absolute and relative imports.
"""

#FIXME: Leverage this rather than magic numbers below.
ABSOLUTE_IMPORT_LEVEL = 0
"""
Constant instructing the builtin `__import__()` function to attempt only
absolute imports.
"""

#FIXME: Leverage this rather than magic numbers below.
DEFAULT_IMPORT_LEVEL = (ABSOLUTE_OR_RELATIVE_IMPORT_LEVEL
                        if sys.version_info[0] == 2 else ABSOLUTE_IMPORT_LEVEL)
"""
Constant instructing the builtin `__import__()` function to attempt the default
import style specific to the active Python interpreter.
Specifically, under:
* Python 2, this defaults to attempting both absolute and relative imports.
* Python 3, this defaults to attempting only absolute imports.
"""

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
_SETUPTOOLS_NAMESPACEPKG_PTHs = (
    "import sys, types, os;has_mfs = sys.version_info > (3, 5);p = os.path.join(sys._getframe(1).f_locals['sitedir'], *('",
    "import sys,types,os; p = os.path.join(sys._getframe(1).f_locals['sitedir'], *('",
    "import sys,new,os; p = os.path.join(sys._getframe(1).f_locals['sitedir'], *('",
    "import sys, types, os;p = os.path.join(sys._getframe(1).f_locals['sitedir'], *('",
    "import sys, types, os;pep420 = sys.version_info > (3, 3);p = os.path.join(sys._getframe(1).f_locals['sitedir'], *('",
)


class DependencyInfo(
        namedtuple("DependencyInfo",
                   ["conditional", "function", "tryexcept", "fromlist"])):
    __slots__ = ()

    def _merged(self, other):
        if (not self.conditional and not self.function and not self.tryexcept) \
           or (not other.conditional and not other.function and not other.tryexcept):
            return DependencyInfo(
                conditional=False,
                function=False,
                tryexcept=False,
                fromlist=self.fromlist and other.fromlist)

        else:
            return DependencyInfo(
                conditional=self.conditional or other.conditional,
                function=self.function or other.function,
                tryexcept=self.tryexcept or other.tryexcept,
                fromlist=self.fromlist and other.fromlist)


def _ast_names(names):
    result = []
    for nm in names:
        if isinstance(nm, ast.alias):
            result.append(nm.name)
        else:
            result.append(nm)

    result = [r for r in result if r != '__main__']
    return result


class _Visitor(ast.NodeVisitor):
    __slots__ = [
        '_module',
        '_level',
        '_in_if',
        '_in_def',
        '_in_try_except',
        'imports',
    ]

    def __init__(self, graph, module):
        self._graph = graph
        self._module = module
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

        # Record this import as originating from this module for subsequent
        # handling by the _process_imports() method.
        self._module._deferred_imports.append(
            (have_star, (name, self._module, fromlist, level), {
                'edge_attr':
                DependencyInfo(
                    conditional=self.in_if,
                    tryexcept=self.in_tryexcept,
                    function=self.in_def,
                    fromlist=False)
            }))

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
