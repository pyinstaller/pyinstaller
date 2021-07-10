import unittest

import os, shutil, sys

from PyInstaller.lib.modulegraph import modulegraph

class ImpliesTestCase(unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, object, types, message=None):
            self.assertTrue(isinstance(object, types),
                    message or '%r is not an instance of %r'%(object, types))

    def testBasicImplies(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-relimport')

        # First check that 'getopt' isn't accidently in the graph:
        mg = modulegraph.ModuleGraph(path=[root]+sys.path)
        mg.add_script(os.path.join(root, 'script.py'))
        node = mg.find_node('mod')
        self.assertIsInstance(node, modulegraph.SourceModule)

        node = mg.find_node('getopt')
        self.assertEqual(node, None)

        # Now check that adding an implied dependency actually adds
        # 'getopt' to the graph:
        mg = modulegraph.ModuleGraph(path=[root]+sys.path, implies={
            'mod': ['getopt']})
        self.assertEqual(node, None)
        mg.add_script(os.path.join(root, 'script.py'))
        node = mg.find_node('mod')
        self.assertIsInstance(node, modulegraph.SourceModule)

        node = mg.find_node('getopt')
        self.assertIsInstance(node, modulegraph.SourceModule)

        # Check that the edges are correct:
        self.assertIn(mg.find_node('mod'), mg.get_edges(node)[1])
        self.assertIn(node, mg.get_edges(mg.find_node('mod'))[0])

    def testPackagedImplies(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-relimport')

        # First check that 'getopt' isn't accidently in the graph:
        mg = modulegraph.ModuleGraph(path=[root]+sys.path)
        mg.add_script(os.path.join(root, 'script.py'))
        node = mg.find_node('mod')
        self.assertIsInstance(node, modulegraph.SourceModule)

        node = mg.find_node('getopt')
        self.assertEqual(node, None)


        # Now check that adding an implied dependency actually adds
        # 'getopt' to the graph:
        mg = modulegraph.ModuleGraph(path=[root]+sys.path, implies={
            'pkg.relative': ['getopt']})
        node = mg.find_node('getopt')
        self.assertEqual(node, None)
        mg.add_script(os.path.join(root, 'script.py'))
        node = mg.find_node('pkg.relative')
        self.assertIsInstance(node, modulegraph.SourceModule)

        node = mg.find_node('getopt')
        self.assertIsInstance(node, modulegraph.SourceModule)

        # Check that the edges are correct:
        self.assertIn(mg.find_node('pkg.relative'), mg.get_edges(node)[1])
        self.assertIn(node, mg.get_edges(mg.find_node('pkg.relative'))[0])


if __name__ == '__main__':
    unittest.main()
