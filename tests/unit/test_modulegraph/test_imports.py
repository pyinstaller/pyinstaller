"""
Test for import machinery
"""
import unittest
import sys
import textwrap
import subprocess
import os
from PyInstaller.lib.modulegraph import modulegraph

class TestNativeImport (unittest.TestCase):
    # The tests check that Python's import statement
    # works as these tests expect.

    def importModule(self, name):
        if '.' in name:
            script = textwrap.dedent("""\
                try:
                    import %s
                except ImportError:
                    import %s
                print (%s.__name__)
            """) %(name, name.rsplit('.', 1)[0], name)
        else:
            script = textwrap.dedent("""\
                import %s
                print (%s.__name__)
            """) %(name, name)

        p = subprocess.Popen([sys.executable, '-c', script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    'testpkg-relimport'),
        )
        data = p.communicate()[0]
        if sys.version_info[0] != 2:
            data = data.decode('UTF-8')
        data = data.strip()

        if data.endswith(' refs]'):
            # with --with-pydebug builds
            data = data.rsplit('\n', 1)[0].strip()

        sts = p.wait()

        if sts != 0:
            print (data)
        self.assertEqual(sts, 0)
        return data


    def testRootModule(self):
        m = self.importModule('mod')
        self.assertEqual(m, 'mod')

    def testRootPkg(self):
        m = self.importModule('pkg')
        self.assertEqual(m, 'pkg')

    def testSubModule(self):
        m = self.importModule('pkg.mod')
        self.assertEqual(m, 'pkg.mod')

    if sys.version_info[0] == 2:
        def testOldStyle(self):
            m = self.importModule('pkg.oldstyle.mod')
            self.assertEqual(m, 'pkg.mod')
    else:
        # python3 always has __future__.absolute_import
        def testOldStyle(self):
            m = self.importModule('pkg.oldstyle.mod')
            self.assertEqual(m, 'mod')

    def testNewStyle(self):
        m = self.importModule('pkg.toplevel.mod')
        self.assertEqual(m, 'mod')

    def testRelativeImport(self):
        m = self.importModule('pkg.relative.mod')
        self.assertEqual(m, 'pkg.mod')

        m = self.importModule('pkg.subpkg.relative.mod')
        self.assertEqual(m, 'pkg.mod')

        m = self.importModule('pkg.subpkg.mod2.mod')
        self.assertEqual(m, 'pkg.sub2.mod')

        m = self.importModule('pkg.subpkg.relative2')
        self.assertEqual(m, 'pkg.subpkg.relative2')

class TestModuleGraphImport (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, value, types):
            if not isinstance(value, types):
                self.fail("%r is not an instance of %r"%(value, types))

    def setUp(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-relimport')
        self.mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        #self.mf.debug = 999
        self.script_name = os.path.join(root, 'script.py')
        self.mf.add_script(self.script_name)

    def testGraphStructure(self):

        # 1. Script to imported modules
        n = self.mf.find_node(self.script_name)
        self.assertIsInstance(n, modulegraph.Script)

        imported = ('mod', 'pkg', 'pkg.mod', 'pkg.oldstyle',
            'pkg.relative', 'pkg.toplevel', 'pkg.subpkg.relative',
            'pkg.subpkg.relative2', 'pkg.subpkg.mod2')

        for nm in imported:
            n2 = self.mf.find_node(nm)
            ed = self.mf.edgeData(n, n2)
            self.assertIsInstance(ed, modulegraph.DependencyInfo)
            self.assertEqual(ed, modulegraph.DependencyInfo(
                fromlist=False, conditional=False, function=False, tryexcept=False))

        refs = self.mf.outgoing(n)
        self.assertEqual(set(refs), set(self.mf.find_node(nm) for nm in imported))

        refs = list(self.mf.incoming(n))
        # The script is a toplevel item and is therefore referred to from the graph root (aka 'None')
        # FIXME fails since PyInstaller skips edges pointing to the current
        # graph, see change 49c725e9f5a79b65923b8e1bfdd794f0f6f7c4bf
        #self.assertEqual(refs, [None])


        # 2. 'mod'
        n = self.mf.find_node('mod')
        self.assertIsInstance(n, modulegraph.SourceModule)
        refs = list(self.mf.outgoing(n))
        self.assertEqual(refs, [])

        #refs = list(self.mf.incoming(n))
        #self.assertEquals(refs, [])

        # 3. 'pkg'
        n = self.mf.find_node('pkg')
        self.assertIsInstance(n, modulegraph.Package)
        refs = list(self.mf.outgoing(n))
        self.maxDiff = None
        self.assertEqual(refs, [n])

        #refs = list(self.mf.incoming(n))
        #self.assertEquals(refs, [])

        # 4. pkg.mod
        n = self.mf.find_node('pkg.mod')
        self.assertIsInstance(n, modulegraph.SourceModule)
        refs = set(self.mf.outgoing(n))
        self.assertEqual(refs, set([self.mf.find_node('pkg')]))
        ed = self.mf.edgeData(n, self.mf.find_node('pkg'))
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(
            fromlist=False, conditional=False, function=False, tryexcept=False))


        # 5. pkg.oldstyle
        n = self.mf.find_node('pkg.oldstyle')
        self.assertIsInstance(n, modulegraph.SourceModule)
        refs = set(self.mf.outgoing(n))
        if sys.version_info[0] == 2:
            n2 = self.mf.find_node('pkg.mod')
        else:
            n2 = self.mf.find_node('mod')
        self.assertEqual(refs, set([self.mf.find_node('pkg'), n2]))
        ed = self.mf.edgeData(n, n2)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(
            fromlist=False, conditional=False, function=False, tryexcept=False))


        # 6. pkg.relative
        n = self.mf.find_node('pkg.relative')
        self.assertIsInstance(n, modulegraph.SourceModule)
        refs = set(self.mf.outgoing(n))
        self.assertEqual(refs, set([self.mf.find_node('__future__'), self.mf.find_node('pkg'), self.mf.find_node('pkg.mod')]))

        ed = self.mf.edgeData(n, self.mf.find_node('pkg.mod'))
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(
            fromlist=True, conditional=False, function=False, tryexcept=False))

        ed = self.mf.edgeData(n, self.mf.find_node('__future__'))
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(
            fromlist=False, conditional=False, function=False, tryexcept=False))

        #ed = self.mf.edgeData(n, self.mf.find_node('__future__.absolute_import'))
        #self.assertIsInstance(ed, modulegraph.DependencyInfo)
        #self.assertEqual(ed, modulegraph.DependencyInfo(
            #fromlist=True, conditional=False, function=False, tryexcept=False))

        # 7. pkg.toplevel
        n = self.mf.find_node('pkg.toplevel')
        self.assertIsInstance(n, modulegraph.SourceModule)
        refs = set(self.mf.outgoing(n))
        self.assertEqual(refs, set([self.mf.find_node('__future__'), self.mf.find_node('pkg'), self.mf.find_node('mod')]))

        ed = self.mf.edgeData(n, self.mf.find_node('mod'))
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(
            fromlist=False, conditional=False, function=False, tryexcept=False))

        ed = self.mf.edgeData(n, self.mf.find_node('__future__'))
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(
            fromlist=False, conditional=False, function=False, tryexcept=False))

        #ed = self.mf.edgeData(n, self.mf.find_node('__future__.absolute_import'))
        #self.assertIsInstance(ed, modulegraph.DependencyInfo)
        #self.assertEqual(ed, modulegraph.DependencyInfo(
            #fromlist=True, conditional=False, function=False, tryexcept=False))

        # 8. pkg.subpkg
        n = self.mf.find_node('pkg.subpkg')
        self.assertIsInstance(n, modulegraph.Package)
        refs = set(self.mf.outgoing(n))
        self.assertEqual(refs, set([self.mf.find_node('pkg')]))

        ed = self.mf.edgeData(n, self.mf.find_node('pkg'))
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(
            fromlist=False, conditional=False, function=False, tryexcept=False))

        # 9. pkg.subpkg.relative
        n = self.mf.find_node('pkg.subpkg.relative')
        self.assertIsInstance(n, modulegraph.SourceModule)
        refs = set(self.mf.outgoing(n))
        self.assertEqual(refs, set([self.mf.find_node('__future__'), self.mf.find_node('pkg'), self.mf.find_node('pkg.subpkg'), self.mf.find_node('pkg.mod')]))

        ed = self.mf.edgeData(n, self.mf.find_node('pkg.subpkg'))
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(
            fromlist=False, conditional=False, function=False, tryexcept=False))

        ed = self.mf.edgeData(n, self.mf.find_node('pkg.mod'))
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(
            fromlist=True, conditional=False, function=False, tryexcept=False))

        # 10. pkg.subpkg.relative2
        n = self.mf.find_node('pkg.subpkg.relative2')
        self.assertIsInstance(n, modulegraph.SourceModule)
        refs = set(self.mf.outgoing(n))
        self.assertEqual(refs, set([self.mf.find_node('pkg.subpkg'), self.mf.find_node('pkg.relimport'), self.mf.find_node('__future__')]))

        # 10. pkg.subpkg.mod2
        n = self.mf.find_node('pkg.subpkg.mod2')
        self.assertIsInstance(n, modulegraph.SourceModule)
        refs = set(self.mf.outgoing(n))
        self.assertEqual(refs, set([
            self.mf.find_node('__future__'),
            self.mf.find_node('pkg.subpkg'),
            self.mf.find_node('pkg.sub2.mod'),
            self.mf.find_node('pkg.sub2'),
        ]))


    def testRootModule(self):
        node = self.mf.find_node('mod')
        self.assertIsInstance(node, modulegraph.SourceModule)
        self.assertEqual(node.identifier, 'mod')

    def testRootPkg(self):
        node = self.mf.find_node('pkg')
        self.assertIsInstance(node, modulegraph.Package)
        self.assertEqual(node.identifier, 'pkg')

    def testSubModule(self):
        node = self.mf.find_node('pkg.mod')
        self.assertIsInstance(node, modulegraph.SourceModule)
        self.assertEqual(node.identifier, 'pkg.mod')

    if sys.version_info[0] == 2:
        def testOldStyle(self):
            node = self.mf.find_node('pkg.oldstyle')
            self.assertIsInstance(node, modulegraph.SourceModule)
            self.assertEqual(node.identifier, 'pkg.oldstyle')
            sub = [ n for n in self.mf.get_edges(node)[0] if n.identifier != '__future__' ][0]
            self.assertEqual(sub.identifier, 'pkg.mod')
    else:
        # python3 always has __future__.absolute_import
        def testOldStyle(self):
            node = self.mf.find_node('pkg.oldstyle')
            self.assertIsInstance(node, modulegraph.SourceModule)
            self.assertEqual(node.identifier, 'pkg.oldstyle')
            sub = [ n for n in self.mf.get_edges(node)[0] if n.identifier != '__future__' ][0]
            self.assertEqual(sub.identifier, 'mod')

    def testNewStyle(self):
        node = self.mf.find_node('pkg.toplevel')
        self.assertIsInstance(node, modulegraph.SourceModule)
        self.assertEqual(node.identifier, 'pkg.toplevel')
        sub = [ n for n in self.mf.get_edges(node)[0] if not n.identifier.startswith('__future__')][0]
        self.assertEqual(sub.identifier, 'mod')

    def testRelativeImport(self):
        node = self.mf.find_node('pkg.relative')
        self.assertIsInstance(node, modulegraph.SourceModule)
        self.assertEqual(node.identifier, 'pkg.relative')
        sub = [ n for n in self.mf.get_edges(node)[0] if not n.identifier.startswith('__future__') ][0]
        self.assertIsInstance(sub, modulegraph.Package)
        self.assertEqual(sub.identifier, 'pkg')

        node = self.mf.find_node('pkg.subpkg.relative')
        self.assertIsInstance(node, modulegraph.SourceModule)
        self.assertEqual(node.identifier, 'pkg.subpkg.relative')
        sub = [ n for n in self.mf.get_edges(node)[0] if not n.identifier.startswith('__future__') ][0]
        self.assertIsInstance(sub, modulegraph.Package)
        self.assertEqual(sub.identifier, 'pkg')

        node = self.mf.find_node('pkg.subpkg.mod2')
        self.assertIsInstance(node, modulegraph.SourceModule)
        self.assertEqual(node.identifier, 'pkg.subpkg.mod2')
        sub = [ n for n in self.mf.get_edges(node)[0] if not n.identifier.startswith('__future__') ][0]
        self.assertIsInstance(sub, modulegraph.SourceModule)
        self.assertEqual(sub.identifier, 'pkg.sub2.mod')

        node = self.mf.find_node('pkg.subpkg.relative2')
        self.assertIsInstance(node, modulegraph.SourceModule)
        self.assertEqual(node.identifier, 'pkg.subpkg.relative2')

        node = self.mf.find_node('pkg.relimport')
        self.assertIsInstance(node, modulegraph.SourceModule)

class TestRegressions1 (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, value, types):
            if not isinstance(value, types):
                self.fail("%r is not an instance of %r", value, types)

    def setUp(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-regr1')
        self.mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        self.mf.add_script(os.path.join(root, 'main_script.py'))

    def testRegr1(self):
        node = self.mf.find_node('pkg.a')
        self.assertIsInstance(node, modulegraph.SourceModule)
        node = self.mf.find_node('pkg.b')
        self.assertIsInstance(node, modulegraph.SourceModule)


    def testMissingPathEntry(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'nosuchdirectory')
        try:
            mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        except os.error:
            self.fail('modulegraph initialiser raises os.error')

class TestRegressions2 (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, value, types):
            if not isinstance(value, types):
                self.fail("%r is not an instance of %r"%(value, types))

    def setUp(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-regr2')
        self.mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        self.mf.add_script(os.path.join(root, 'main_script.py'))

    def testRegr1(self):
        node = self.mf.find_node('pkg.base')
        self.assertIsInstance(node, modulegraph.SourceModule)
        node = self.mf.find_node('pkg.pkg')
        self.assertIsInstance(node, modulegraph.SourceModule)

class TestRegressions3 (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, value, types):
            if not isinstance(value, types):
                self.fail("%r is not an instance of %r"%(value, types))

    def assertStartswith(self, value, test):
        if not value.startswith(test):
            self.fail("%r does not start with %r"%(value, test))

    def setUp(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-regr3')
        self.mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        self.mf.add_script(os.path.join(root, 'script.py'))

    @unittest.skipUnless(not hasattr(sys, 'real_prefix'), "Test doesn't work in virtualenv")
    def testRegr1(self):
        node = self.mf.find_node('mypkg.distutils')
        self.assertIsInstance(node, modulegraph.Package)
        node = self.mf.find_node('mypkg.distutils.ccompiler')
        self.assertIsInstance(node, modulegraph.SourceModule)
        self.assertStartswith(node.filename, os.path.dirname(__file__))

        import distutils.sysconfig, distutils.ccompiler
        node = self.mf.find_node('distutils.ccompiler')
        self.assertIsInstance(node, modulegraph.SourceModule)
        self.assertEqual(os.path.dirname(node.filename),
                os.path.dirname(distutils.ccompiler.__file__))

        node = self.mf.find_node('distutils.sysconfig')
        self.assertIsInstance(node, modulegraph.SourceModule)
        self.assertEqual(os.path.dirname(node.filename),
                os.path.dirname(distutils.sysconfig.__file__))

class TestRegression4 (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, value, types):
            if not isinstance(value, types):
                self.fail("%r is not an instance of %r"%(value, types))

    def setUp(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-regr4')
        self.mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        self.mf.add_script(os.path.join(root, 'script.py'))

    def testRegr1(self):
        node = self.mf.find_node('pkg.core')
        self.assertIsInstance(node, modulegraph.Package)

        node = self.mf.find_node('pkg.core.callables')
        self.assertIsInstance(node, modulegraph.SourceModule)

        node = self.mf.find_node('pkg.core.listener')
        self.assertIsInstance(node, modulegraph.SourceModule)

        node = self.mf.find_node('pkg.core.listenerimpl')
        self.assertIsInstance(node, modulegraph.SourceModule)

class TestRegression5 (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, value, types):
            if not isinstance(value, types):
                self.fail("%r is not an instance of %r"%(value, types))

    def setUp(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-regr5')
        self.mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        self.mf.add_script(os.path.join(root, 'script.py'))

    def testRegr1(self):
        node = self.mf.find_node('distutils')
        self.assertIsInstance(node, modulegraph.Package)
        self.assertIn(os.path.join('distutils', '__init__'), node.filename)


class TestRelativeReferenceToToplevel (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, value, types):
            if not isinstance(value, types):
                self.fail("%r is not an instance of %r"%(value, types))

    def test_relative_import_too_far(self):
        # pkg.mod tries to import "..sys" (outside of the package...)
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-regr7')
        mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        mf.add_script(os.path.join(root, 'script.py'))

        m = mf.find_node('')
        self.assertIs(m, None)

        m = mf.find_node('pkg.mod')
        self.assertIsInstance(m, modulegraph.SourceModule)

        imported = list(mf.get_edges(m)[0])
        self.assertEqual(len(imported), 5)

        im = imported[0]
        self.assertIsInstance(im, modulegraph.InvalidRelativeImport)
        self.assertEqual(im.relative_path, '..')
        self.assertEqual(im.from_name, 'sys')
        self.assertEqual(im.identifier, '..sys')

        im1 = imported[1]
        im2 = imported[2]
        if im1.identifier == '...xml':
            # Order of modules imported in a single 'from .. import a, b' list
            # is unspecified, ensure a fixed order for this test.
            im2, im1 = im1, im2

        self.assertIsInstance(im1, modulegraph.InvalidRelativeImport)
        self.assertEqual(im1.relative_path, '...')
        self.assertEqual(im1.from_name, 'os')
        self.assertEqual(im1.identifier, '...os')

        im = imported[2]
        self.assertIsInstance(im2, modulegraph.InvalidRelativeImport)
        self.assertEqual(im2.relative_path, '...')
        self.assertEqual(im2.from_name, 'xml')
        self.assertEqual(im2.identifier, '...xml')

        im = imported[3]
        self.assertIsInstance(im, modulegraph.InvalidRelativeImport)
        self.assertEqual(im.relative_path, '..foo')
        self.assertEqual(im.from_name, 'bar')
        self.assertEqual(im.identifier, '..foo.bar')

        im = imported[4]
        self.assertIs(im, mf.find_node('pkg'))

class TestInvalidAsyncFunction (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, value, types):
            if not isinstance(value, types):
                self.fail("%r is not an instance of %r"%(value, types))

    @unittest.skipUnless(sys.version_info[:2] == (3,5), "Requires python 3.5")
    def test_invalid_async_function(self):
        # In python 3.5 the following function is invalid:
        #
        #    async def foo():
        #       yield 1
        #
        # This is a syntax error that's reported when compiling the AST
        # to bytecode, which caused an error in modulegraph.
        #
        # In python 3.6 this is valid code (and in earlier versions async
        # versions didn't exist)
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-regr8')
        mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        mf.add_script(os.path.join(root, 'script.py'))

        n = mf.find_node('mod')
        self.assertIsInstance(n, modulegraph.InvalidSourceModule)

if __name__ == "__main__":
    unittest.main()
