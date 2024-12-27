import unittest
from PyInstaller.lib.modulegraph import modulegraph
import os
import sys
import shutil
import warnings
from altgraph import Graph
from PyInstaller.compat import is_win, is_cygwin
from PyInstaller.utils.tests import importorskip, skipif
import textwrap
import pickle
from io import StringIO

from importlib._bootstrap_external import SourceFileLoader, ExtensionFileLoader
from zipimport import zipimporter


TESTDATA = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "testdata", "nspkg")

try:
    expectedFailure = unittest.expectedFailure
except AttributeError:
    import functools
    def expectedFailure(function):
        @functools.wraps(function)
        def wrapper(*args, **kwds):
            try:
                function(*args, **kwds)
            except AssertionError:
                pass

            else:
                self.fail("unexpected pass")

class TestDependencyInfo (unittest.TestCase):
    def test_pickling(self):
        info = modulegraph.DependencyInfo(function=True, conditional=False, tryexcept=True, fromlist=False)
        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            b = pickle.dumps(info, proto)
            self.assertTrue(isinstance(b, bytes))

            o = pickle.loads(b)
            self.assertEqual(o, info)

    def test_merging(self):
        info1 = modulegraph.DependencyInfo(function=True, conditional=False, tryexcept=True, fromlist=False)
        info2 = modulegraph.DependencyInfo(function=False, conditional=True, tryexcept=True, fromlist=False)
        self.assertEqual(
            info1._merged(info2), modulegraph.DependencyInfo(function=True, conditional=True, tryexcept=True, fromlist=False))

        info2 = modulegraph.DependencyInfo(function=False, conditional=True, tryexcept=False, fromlist=False)
        self.assertEqual(
            info1._merged(info2), modulegraph.DependencyInfo(function=True, conditional=True, tryexcept=True, fromlist=False))

        info2 = modulegraph.DependencyInfo(function=False, conditional=False, tryexcept=False, fromlist=False)
        self.assertEqual(
            info1._merged(info2), modulegraph.DependencyInfo(function=False, conditional=False, tryexcept=False, fromlist=False))

        info1 = modulegraph.DependencyInfo(function=True, conditional=False, tryexcept=True, fromlist=True)
        self.assertEqual(
            info1._merged(info2), modulegraph.DependencyInfo(function=False, conditional=False, tryexcept=False, fromlist=False))

        info2 = modulegraph.DependencyInfo(function=False, conditional=False, tryexcept=False, fromlist=True)
        self.assertEqual(
            info1._merged(info2), modulegraph.DependencyInfo(function=False, conditional=False, tryexcept=False, fromlist=True))


class TestFunctions (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, obj, types):
            self.assertTrue(isinstance(obj, types), '%r is not instance of %r'%(obj, types))

    # The test package (and its .zip and .egg variants) do not contain dummy extension file with .dll suffix, which
    # would be required for the test under Cygwin.
    @skipif(
        is_cygwin,
        reason="Does not account for the .dll suffix used for extension modules under Cygwin.",
    )
    def test_find_module(self):
        for path in ('syspath', 'syspath.zip', 'syspath.egg'):
            path = os.path.join(os.path.dirname(TESTDATA), path)
            if os.path.exists(os.path.join(path, 'mymodule.pyc')):
                os.unlink(os.path.join(path, 'mymodule.pyc'))

            # Plain module
            modgraph = modulegraph.ModuleGraph()
            info = modgraph._find_module('mymodule', path=[path] + sys.path)

            filename, loader = info

            if path.endswith('.zip') or path.endswith('.egg'):
                # Zip importers may precompile
                if filename.endswith('.py'):
                    self.assertEqual(filename, os.path.join(path, 'mymodule.py'))
                    self.assertIsInstance(loader, zipimporter)

                else:
                    self.assertEqual(filename, os.path.join(path, 'mymodule.pyc'))
                    self.assertIsInstance(loader, zipimporter)

            else:
                self.assertEqual(filename, os.path.join(path, 'mymodule.py'))
                self.assertIsInstance(loader, SourceFileLoader)

            # Compiled plain module, no source
            if path.endswith('.zip') or path.endswith('.egg'):
                self.assertRaises(ImportError, modgraph._find_module, 'mymodule2', path=[path] + sys.path)

            else:
                info = modgraph._find_module('mymodule2', path=[path] + sys.path)

                filename, loader = info

                self.assertEqual(filename, os.path.join(path, 'mymodule2.pyc'))


            # Compiled plain module, with source
#            info = modgraph._find_module('mymodule3', path=[path] + sys.path)
#
#            fp = info[0]
#            filename = info[1]
#            description = info[2]
#
#            self.assertTrue(hasattr(fp, 'read'))
#
#            if sys.version_info[:2] >= (3,2):
#                self.assertEqual(filename, os.path.join(path, '__pycache__', 'mymodule3.cpython-32.pyc'))
#            else:
#                self.assertEqual(filename, os.path.join(path, 'mymodule3.pyc'))
#            self.assertEqual(description, ('.pyc', 'rb', imp.PY_COMPILED))


            # Package
            info = modgraph._find_module('mypkg', path=[path] + sys.path)

            filename, loader = info

            # FIXME: PyInstaller appends `__init__.py` to the pkg-directory
            #self.assertEqual(filename, os.path.join(path, 'mypkg'))
            self.assertTrue(loader.is_package("mypkg"))

            # Extension
            if path.endswith('.zip'):
                self.assertRaises(ImportError, modgraph._find_module, 'myext', path=[path] + sys.path)

            elif path.endswith('.egg'):
                # FIXME: restore modulegraph's behaviour
                # For a zipped egg modulegraph finds 'myext.so', while
                # PyInstaller (using the import machinery) finds 'myext.py'
                # which is contained in the test-data .egg, too.
                #
                # See https://bitbucket.org/ronaldoussoren/modulegraph/issues/34
                #
                # ronaldoussoren says: "The behavior is intentional and only
                # for .egg archives. The reason is to match behavior of
                # setuptools: setuptools will create an .egg archive that
                # contains the C extension as well as a python module of the
                # same name that extras the C extensions into a tempdir and
                # than loads it. By preferring the .so file over a .py file in
                # eggs the modulegraph is more useful as the .py file is
                # generally just a hack to fake support for loading .so files
                # from an archive."
                pass
            else:
                info = modgraph._find_module('myext', path=[path] + sys.path)
                filename, loader = info

                if sys.platform == 'win32':
                    ext = '.pyd'
                elif sys.platform == 'cygwin':
                    ext = '.dll'
                else:
                    # This is a lie, but is good enough for now
                    ext = '.so'

                self.assertEqual(filename, os.path.join(path, 'myext' + ext))
                self.assertIsInstance(loader, ExtensionFileLoader)


class TestNode (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, obj, types):
            self.assertTrue(isinstance(obj, types), '%r is not instance of %r'%(obj, types))
    def testBasicAttributes(self):
        n = modulegraph.Node("foobar.xyz")
        self.assertEqual(n.identifier, n.graphident)
        self.assertEqual(n.identifier, 'foobar.xyz')
        self.assertEqual(n.filename, None)
        self.assertEqual(n.packagepath, None)
        self.assertEqual(n.code, None)
        self.assertEqual(n._deferred_imports, None)
        self.assertEqual(n._starimported_ignored_module_names, set())

    def test_global_attrs(self):
        n = modulegraph.Node("foobar.xyz")
        self.assertEqual(n._global_attr_names, set())

        self.assertFalse(n.is_global_attr('foo'))
        n.add_global_attr('foo')
        self.assertTrue(n.is_global_attr('foo'))
        n.remove_global_attr_if_found('foo')
        self.assertFalse(n.is_global_attr('foo'))
        # removing then name again must not fail
        n.remove_global_attr_if_found('foo')

    def test_submodules(self):
        n = modulegraph.Node("foobar.xyz")
        self.assertEqual(n._submodule_basename_to_node, {})

        sm = modulegraph.Node("bar.baz")
        self.assertFalse(n.is_submodule('bar'))
        n.add_submodule('bar', sm)
        self.assertTrue(n.is_submodule('bar'))
        self.assertIs(n.get_submodule('bar'), sm)
        self.assertRaises(KeyError, n.get_submodule, 'XXX')
        self.assertIs(n.get_submodule_or_none('XXX'), None)

    def testOrder(self):
        n1 = modulegraph.Node("n1")
        n2 = modulegraph.Node("n2")

        self.assertTrue(n1 < n2)
        self.assertFalse(n2 < n1)
        self.assertTrue(n1 <= n1)
        self.assertFalse(n1 == n2)
        self.assertTrue(n1 == n1)
        self.assertTrue(n1 != n2)
        self.assertFalse(n1 != n1)
        self.assertTrue(n2 > n1)
        self.assertFalse(n1 > n2)
        self.assertTrue(n1 >= n1)
        self.assertTrue(n2 >= n1)

    def testHashing(self):
        n1a = modulegraph.Node('n1')
        n1b = modulegraph.Node('n1')
        n2 = modulegraph.Node('n2')

        d = {}
        d[n1a] = 'n1'
        d[n2] = 'n2'
        self.assertEqual(d[n1b], 'n1')
        self.assertEqual(d[n2], 'n2')

    def test_infoTuple(self):
        n = modulegraph.Node('n1')
        self.assertEqual(n.infoTuple(), ('n1',))

    @staticmethod
    def _cleanup_class_dict(klass):
        d = dict(klass.__dict__)
        d.pop('__doc__', None)
        d.pop('__module__', None)
        d.pop('__weakref__', None)
        d.pop('__qualname__', None)  # New in Python 3.3
        d.pop('__dict__', None) # New in Python 3.4
        d.pop('__slotnames__', None)
        d.pop('__firstlineno__', None)  # Python 3.13
        d.pop('__static_attributes__', None)  # Python 3.13
        return d

    def assertNoMethods(self, klass):
        d = self._cleanup_class_dict(klass)
        self.assertEqual(d, {})

    def assertHasExactMethods(self, klass, *methods):
        d = self._cleanup_class_dict(klass)
        for nm in methods:
            self.assertTrue(nm in d, "%s doesn't have attribute %r"%(klass, nm))
            del d[nm]

        self.assertEqual(d, {})


    if not hasattr(unittest.TestCase, 'assertIsSubclass'):
        def assertIsSubclass(self, cls1, cls2, message=None):
            self.assertTrue(issubclass(cls1, cls2),
                    message or "%r is not a subclass of %r"%(cls1, cls2))

    def test_subclasses(self):
        self.assertIsSubclass(modulegraph.AliasNode, modulegraph.Node)
        self.assertIsSubclass(modulegraph.Script, modulegraph.Node)
        self.assertIsSubclass(modulegraph.BadModule, modulegraph.Node)
        self.assertIsSubclass(modulegraph.ExcludedModule, modulegraph.BadModule)
        self.assertIsSubclass(modulegraph.MissingModule, modulegraph.BadModule)
        self.assertIsSubclass(modulegraph.BaseModule, modulegraph.Node)
        self.assertIsSubclass(modulegraph.BuiltinModule, modulegraph.BaseModule)
        self.assertIsSubclass(modulegraph.SourceModule, modulegraph.BaseModule)
        self.assertIsSubclass(modulegraph.CompiledModule, modulegraph.BaseModule)
        self.assertIsSubclass(modulegraph.Package, modulegraph.BaseModule)
        self.assertIsSubclass(modulegraph.Extension, modulegraph.BaseModule)

        # These classes have no new functionality, check that no code
        # got added:
        self.assertNoMethods(modulegraph.BadModule)
        self.assertNoMethods(modulegraph.ExcludedModule)
        self.assertNoMethods(modulegraph.MissingModule)
        self.assertNoMethods(modulegraph.BuiltinModule)
        self.assertNoMethods(modulegraph.SourceModule)
        self.assertNoMethods(modulegraph.CompiledModule)
        self.assertNoMethods(modulegraph.Package)
        self.assertNoMethods(modulegraph.Extension)

        # AliasNode is basically a clone of an existing node
        self.assertHasExactMethods(modulegraph.Script, '__init__', 'infoTuple')
        n1 = modulegraph.Node('n1')
        n1.packagepath = ['a', 'b']

        a1 = modulegraph.AliasNode('a1', n1)
        self.assertEqual(a1.graphident, 'a1')
        self.assertEqual(a1.identifier, 'n1')
        self.assertTrue(a1.packagepath is n1.packagepath)

        self.assertIs(a1._deferred_imports, None)
        self.assertIs(a1._global_attr_names, n1._global_attr_names)
        self.assertIs(a1._starimported_ignored_module_names,
                      n1._starimported_ignored_module_names)
        self.assertIs(a1._submodule_basename_to_node,
                      n1._submodule_basename_to_node)

        v = a1.infoTuple()
        self.assertEqual(v, ('a1', 'n1'))

        # Scripts have a filename
        self.assertHasExactMethods(modulegraph.Script, '__init__', 'infoTuple')
        s1 = modulegraph.Script('do_import')
        self.assertEqual(s1.graphident, 'do_import')
        self.assertEqual(s1.identifier, 'do_import')
        self.assertEqual(s1.filename, 'do_import')

        v = s1.infoTuple()
        self.assertEqual(v, ('do_import',))

        # BaseModule adds some attributes and a custom infotuple
        self.assertHasExactMethods(modulegraph.BaseModule, '__init__', 'infoTuple')
        m1 = modulegraph.BaseModule('foo')
        self.assertEqual(m1.graphident, 'foo')
        self.assertEqual(m1.identifier, 'foo')
        self.assertEqual(m1.filename, None)
        self.assertEqual(m1.packagepath, None)

        m1 = modulegraph.BaseModule('foo', 'bar',  ['a'])
        self.assertEqual(m1.graphident, 'foo')
        self.assertEqual(m1.identifier, 'foo')
        self.assertEqual(m1.filename, 'bar')
        self.assertEqual(m1.packagepath, ['a'])

class TestModuleGraph (unittest.TestCase):
    # Test for class modulegraph.modulegraph.ModuleGraph
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, obj, types):
            self.assertTrue(isinstance(obj, types), '%r is not instance of %r'%(obj, types))

    def test_constructor(self):
        o = modulegraph.ModuleGraph()
        self.assertTrue(o.path is sys.path)
        self.assertEqual(o.lazynodes, {})
        self.assertEqual(o.replace_paths, ())
        self.assertEqual(o.debug, 0)

        # Stricter tests would be nice, but that requires
        # better control over what's on sys.path

        g = Graph.Graph()
        o = modulegraph.ModuleGraph(['a', 'b', 'c'], ['modA'], [
                ('fromA', 'toB'), ('fromC', 'toD')],
                {
                    'modA': ['modB', 'modC'],
                    'modC': ['modE', 'modF'],
                }, g, 1)
        self.assertEqual(o.path, ['a', 'b', 'c'])
        self.assertEqual(o.lazynodes, {
            'modA': None,
            'modC': ['modE', 'modF'],
        })
        self.assertEqual(o.replace_paths, [('fromA', 'toB'), ('fromC', 'toD')])
        self.assertTrue(o.graph is g)
        self.assertEqual(o.debug, 1)

    def testImpliedReference(self):
        graph = modulegraph.ModuleGraph()

        record = []
        def import_hook(*args):
            record.append(('import_hook',) + args)
            return [graph.createNode(modulegraph.Node, args[0])]

        def _safe_import_hook(*args):
            record.append(('_safe_import_hook',) + args)
            return [graph.createNode(modulegraph.Node, args[0])]

        graph.import_hook = import_hook
        graph._safe_import_hook = _safe_import_hook

        n1 = graph.createNode(modulegraph.Node, 'n1')
        n2 = graph.createNode(modulegraph.Node, 'n2')

        graph.implyNodeReference(n1, n2)
        outs, ins = map(list, graph.get_edges(n1))
        self.assertEqual(outs, [n2])
        self.assertEqual(ins, [])

        self.assertEqual(record, [])

        graph.implyNodeReference(n2, "n3")
        n3 = graph.find_node('n3')
        outs, ins = map(list, graph.get_edges(n2))
        self.assertEqual(outs, [n3])
        self.assertEqual(ins, [n1])
        self.assertEqual(record, [
            ('_safe_import_hook', 'n3', n2, None)
        ])



    @expectedFailure
    def test_findNode(self):
        self.fail("findNode")

    def test_run_script(self):
        script = os.path.join(os.path.dirname(TESTDATA), 'script')

        graph = modulegraph.ModuleGraph()
        master = graph.createNode(modulegraph.Node, 'root')
        m = graph.add_script(script, master)
        self.assertEqual(list(graph.get_edges(master)[0])[0], m)
        self.assertEqual(set(graph.get_edges(m)[0]), set([
            graph.find_node('sys'),
            graph.find_node('os'),
        ]))

    @expectedFailure
    def test_import_hook(self):
        self.fail("import_hook")

    def test_determine_parent(self):
        graph = modulegraph.ModuleGraph()
        # FIXME PyInstaller: original _load_tail returned a MissingModule if
        # the module was not found. PyInstaller changed this in
        # cae47e4f5b51a94ac3ceb5d093283ba0cc895589 and raises an ImportError,
        # which makes these two calls fail.
        #graph.import_hook('os.path', None)
        #graph.import_hook('idlelib', None)
        graph.import_hook('xml.dom', None)

        for node in graph.nodes():
            if isinstance(node, modulegraph.Package):
                break
        else:
            self.fail("No package located, should have at least 'os'")

        self.assertIsInstance(node, modulegraph.Package)
        parent = graph._determine_parent(node)
        self.assertEqual(parent.identifier, node.identifier)
        self.assertEqual(parent, graph.find_node(node.identifier))
        self.assertTrue(isinstance(parent, modulegraph.Package))

        # XXX: Might be a usecase for some odd code in determine_parent...
        #node = modulegraph.Package('encodings')
        #node.packagepath = parent.packagepath
        #m = graph._determine_parent(node)
        #self.assertTrue(m is parent)

        m = graph.find_node('xml')
        self.assertEqual(graph._determine_parent(m), m)

        m = graph.find_node('xml.dom')
        self.assertEqual(graph._determine_parent(m), graph.find_node('xml.dom'))


    @expectedFailure
    def test_find_head_package(self):
        self.fail("find_head_package")


    @expectedFailure
    def test_ensure_fromlist(self):
        # 1. basic 'from module import name, name'
        # 2. 'from module import *'
        # 3. from module import os
        #    (where 'os' is not a name in 'module',
        #     should create MissingModule node, and
        #     should *not* refer to the global os)
        self.fail("ensure_fromlist")

    @expectedFailure
    def test_find_all_submodules(self):
        # 1. basic
        # 2. no packagepath (basic module)
        # 3. extensions, python modules
        # 4. with/without zipfile
        # 5. files that aren't python modules/extensions
        self.fail("find_all_submodules")

    @expectedFailure
    def test_import_module(self):
        self.fail("import_module")

    @expectedFailure
    def test_load_module(self):
        self.fail("load_module")

    @expectedFailure
    def test_safe_import_hook(self):
        self.fail("safe_import_hook")

    @expectedFailure
    def test_scan_code(self):
        mod = modulegraph.Node('root')

        graph = modulegraph.ModuleGraph()
        code = compile('', '<test>', 'exec', 0, False)
        graph.scan_code(code, mod)
        self.assertEqual(list(graph.nodes()), [])

        node_map = {}
        def _safe_import(name, mod, fromlist, level):
            if name in node_map:
                node = node_map[name]
            else:
                node = modulegraph.Node(name)
            node_map[name] = node
            return [node]

        graph = modulegraph.ModuleGraph()
        graph._safe_import_hook = _safe_import

        code = compile(textwrap.dedent('''\
            import sys
            import os.path

            def testfunc():
                import shutil
            '''), '<test>', 'exec', 0, False)
        graph.scan_code(code, mod)
        modules = [node.identifier for node in graph.nodes()]
        self.assertEqual(set(node_map), set(['sys', 'os.path', 'shutil']))


        # from module import a, b, c
        # from module import *
        #  both:
        #   -> with/without globals
        #   -> with/without modules in globals (e.g,
        #       from os import * adds dependency to os.path)
        # from .module import a
        # from ..module import a
        #   -> check levels
        # import name
        # import a.b
        #   -> should add dependency to a
        # try to build case where commented out
        # code would behave different than current code
        # (Carbon.SomeMod contains 'import Sibling' seems
        # to cause difference in real code)

        self.fail("actual test needed")



    @expectedFailure
    def test_load_package(self):
        self.fail("load_package")

    def test_find_module(self):
        record = []
        class MockedModuleGraph(modulegraph.ModuleGraph):
            def _find_module(self, name, path, parent=None):
                if path == None:
                    path = sys.path
                record.append((name, path))
                return super(MockedModuleGraph, self)._find_module(name, path, parent)

        mockedgraph = MockedModuleGraph()
        try:
            graph = modulegraph.ModuleGraph()
            m = graph._find_module('sys', None)
            self.assertEqual(record, [])
            self.assertEqual(m, (None, modulegraph.BUILTIN_MODULE))

            xml = graph.import_hook("xml")[0]
            self.assertEqual(xml.identifier, 'xml')

            self.assertRaises(ImportError, graph._find_module, 'xml', None)

            self.assertEqual(record, [])
            m = mockedgraph._find_module('shutil', None)
            self.assertEqual(record, [
                ('shutil', graph.path),
            ])
            self.assertTrue(isinstance(m, tuple))
            self.assertEqual(len(m), 2)
            srcfn = shutil.__file__
            if srcfn.endswith('.pyc'):
                srcfn = srcfn[:-1]
            self.assertEqual(os.path.realpath(m[0]), os.path.realpath(srcfn))
            self.assertIsInstance(m[1], SourceFileLoader)

            m2 = graph._find_module('shutil', None)
            self.assertEqual(m[1:], m2[1:])


            record[:] = []
            m = mockedgraph._find_module('sax', xml.packagepath, xml)
            # FIXME: PyInstaller appends `__init__.py` to the pkg-directory
            #self.assertEqual(m,
            #        (None, os.path.join(os.path.dirname(xml.filename), 'sax'),
            #        ('', '', imp.PKG_DIRECTORY)))
            self.assertEqual(record, [
                ('sax', xml.packagepath),
            ])

        finally:
            pass

    @expectedFailure
    def test_create_xref(self):
        self.fail("create_xref")

    @expectedFailure
    def test_itergraphreport(self):
        self.fail("itergraphreport")

    def test_report(self):
        graph = modulegraph.ModuleGraph()

        saved_stdout = sys.stdout
        try:
            fp = sys.stdout = StringIO()
            graph.report()
            lines = fp.getvalue().splitlines()
            fp.close()

            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[0], '')
            self.assertEqual(lines[1], 'Class           Name                      File')
            self.assertEqual(lines[2], '-----           ----                      ----')

            fp = sys.stdout = StringIO()
            graph._safe_import_hook('os', None, ())
            graph._safe_import_hook('sys', None, ())
            graph._safe_import_hook('nomod', None, ())
            graph.report()
            lines = fp.getvalue().splitlines()
            fp.close()

            self.assertEqual(lines[0], '')
            self.assertEqual(lines[1], 'Class           Name                      File')
            self.assertEqual(lines[2], '-----           ----                      ----')
            expected = []
            for n in graph.iter_graph():
                if n.filename:
                    expected.append([type(n).__name__, n.identifier, n.filename])
                else:
                    expected.append([type(n).__name__, n.identifier])

            expected.sort()
            actual = [item.split() for item in lines[3:]]
            actual.sort()
            self.assertEqual(expected, actual)


        finally:
            sys.stdout = saved_stdout

    def test_graphreport(self):

        def my_iter(flatpackages="packages"):
            yield "line1\n"
            yield str(flatpackages) + "\n"
            yield "line2\n"

        graph = modulegraph.ModuleGraph()
        graph.itergraphreport = my_iter

        fp = StringIO()
        graph.graphreport(fp)
        self.assertEqual(fp.getvalue(), "line1\n()\nline2\n")

        fp = StringIO()
        graph.graphreport(fp, "deps")
        self.assertEqual(fp.getvalue(), "line1\ndeps\nline2\n")

        saved_stdout = sys.stdout
        try:
            sys.stdout = fp = StringIO()
            graph.graphreport()
            self.assertEqual(fp.getvalue(), "line1\n()\nline2\n")

        finally:
            sys.stdout = saved_stdout


    def test_replace_paths_in_code(self):
        join = os.path.join # shortcut
        graph = modulegraph.ModuleGraph(replace_paths=[
                ('path1', 'path2'),
                (join('path3', 'path5'), 'path4'),
            ])

        co = compile(textwrap.dedent("""
        [x for x in range(4)]
        """), join("path4", "index.py"), 'exec', 0, 1)
        co = graph._replace_paths_in_code(co)
        self.assertEqual(co.co_filename, join('path4', 'index.py'))

        co = compile(textwrap.dedent("""
        [x for x in range(4)]
        (x for x in range(4))
        """), join("path1", "index.py"), 'exec', 0, 1)
        self.assertEqual(co.co_filename, join('path1', 'index.py'))
        co = graph._replace_paths_in_code(co)
        self.assertEqual(co.co_filename, join('path2', 'index.py'))
        for c in co.co_consts:
            if isinstance(c, type(co)):
                self.assertEqual(c.co_filename, join('path2', 'index.py'))

        co = compile(textwrap.dedent("""
        [x for x in range(4)]
        """), join("path3", "path4", "index.py"), 'exec', 0, 1)
        co = graph._replace_paths_in_code(co)
        self.assertEqual(co.co_filename, join('path3', 'path4', 'index.py'))

        co = compile(textwrap.dedent("""
        [x for x in range(4)]
        """), join("path3", "path5.py"), 'exec', 0, 1)
        co = graph._replace_paths_in_code(co)
        self.assertEqual(co.co_filename, join('path3', 'path5.py'))

        co = compile(textwrap.dedent("""
        [x for x in range(4)]
        """), join("path3", "path5", "index.py"), 'exec', 0, 1)
        co = graph._replace_paths_in_code(co)
        self.assertEqual(co.co_filename, join('path4', 'index.py'))

    def test_createReference(self):
        graph = modulegraph.ModuleGraph()
        n1 = modulegraph.Node('n1')
        n2 = modulegraph.Node('n2')
        graph.addNode(n1)
        graph.addNode(n2)

        graph.add_edge(n1, n2)
        outs, ins = map(list, graph.get_edges(n1))
        self.assertEqual(outs, [n2])
        self.assertEqual(ins, [])
        outs, ins = map(list, graph.get_edges(n2))
        self.assertEqual(outs, [])
        self.assertEqual(ins, [n1])

        e = graph.graph.edge_by_node('n1', 'n2')
        self.assertIsInstance(e, int)
        self.assertEqual(graph.graph.edge_data(e), 'direct')

    @importorskip('lxml')
    def test_create_xref(self):
        # XXX: This test is far from optimal, it just ensures
        # that all code is exercised to catch small bugs and
        # py3k issues without verifying that the code actually
        # works....
        graph = modulegraph.ModuleGraph()
        if __file__.endswith('.py'):
            graph.add_script(__file__)
        else:
            graph.add_script(__file__[:-1])

        graph.import_hook('os')
        graph.import_hook('xml.etree')
        graph.import_hook('unittest')

        fp = StringIO()
        graph.create_xref(out=fp)

        data = fp.getvalue()
        # Don't tolerate any HTML `parsing errors <https://lxml.de/parsing.html#parser-options>`_.
        from lxml import etree
        parser = etree.HTMLParser(recover=False)
        tree = etree.parse(StringIO(data), parser)
        assert tree is not None
        # Verify no `errors <https://lxml.de/parsing.html#error-log>`_ occurred.
        assert len(parser.error_log) == 0

    @importorskip('lib2to3')  # lib2to3 was removed in python 3.13
    def test_itergraphreport(self):
        # XXX: This test is far from optimal, it just ensures
        # that all code is exercised to catch small bugs and
        # py3k issues without verifying that the code actually
        # works....
        graph = modulegraph.ModuleGraph()
        if __file__.endswith('.py'):
            graph.add_script(__file__)
        else:
            graph.add_script(__file__[:-1])
        graph.import_hook('os')
        graph.import_hook('xml.etree')
        graph.import_hook('unittest')
        # Upstream uses 'distutils.command.build', but this does not work at
        # Travis which uses a virtualenv (PyInstaller has a
        # pre_find_module_path hook for this case, plain modulegraph can't
        # handle this).
        graph.import_hook('lib2to3.fixes.fix_apply')

        fp = StringIO()
        list(graph.itergraphreport())

        # XXX: platpackages isn't implemented, and is undocumented hence
        # it is unclear what this is intended to be...
        #list(graph.itergraphreport(flatpackages=...))


if __name__ == "__main__":
    unittest.main()
