import sys
import unittest
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
                'testpkg-import-from-init'),
            encoding='utf8',
        )
        data = p.communicate()[0]
        data = data.strip()

        if data.endswith(' refs]'):
            # with --with-pydebug builds
            data = data.rsplit('\n', 1)[0].strip()

        sts = p.wait()

        if sts != 0:
            print (data)
        self.assertEqual(sts, 0)
        return data

    def testRootPkgRelImport(self):
        m = self.importModule('pkg2')
        self.assertEqual(m, 'pkg2')

    def testSubPackageRelImport(self):
        m = self.importModule('pkg2.subpkg')
        self.assertEqual(m, 'pkg2.subpkg')


class TestModuleGraphImport (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, value, types):
            if not isinstance(value, types):
                self.fail("%r is not an instance of %r"%(value, types))

    def setUp(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-import-from-init')
        self.mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        #self.mf.debug = 999
        self.mf.add_script(os.path.join(root, 'script.py'))

    def testRootPkgRelImport(self):
        node = self.mf.find_node('pkg2')
        self.assertIsInstance(node, modulegraph.Package)
        self.assertEqual(node.identifier, 'pkg2')

    def testSubPackageRelImport(self):
        node = self.mf.find_node('pkg2.subpkg')
        self.assertIsInstance(node, modulegraph.Package)
        self.assertEqual(node.identifier, 'pkg2.subpkg')

        node = self.mf.find_node('pkg2.subpkg.compat')
        self.assertIsInstance(node, modulegraph.SourceModule)
        self.assertEqual(node.identifier, 'pkg2.subpkg.compat')

        node = self.mf.find_node('pkg2.subpkg._collections')
        self.assertIsInstance(node, modulegraph.SourceModule)
        self.assertEqual(node.identifier, 'pkg2.subpkg._collections')


if __name__ == "__main__":
    unittest.main()
