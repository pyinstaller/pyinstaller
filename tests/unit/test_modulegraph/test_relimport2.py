"""
Test for import machinery
"""
import unittest
import sys
import textwrap
import subprocess
import os
from PyInstaller.lib.modulegraph import modulegraph

class TestModuleGraphImport (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, value, types):
            if not isinstance(value, types):
                self.fail("%r is not an instance of %r"%(value, types))

    def setUp(self):
        self.root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-relimport2')
        self.mf = modulegraph.ModuleGraph(path=[ self.root ] + sys.path)


    def test_init_as_script(self):
        self.mf.add_script(os.path.join(self.root, 'pkg/__init__.py'))
        n = self.mf.find_node('mod1')
        self.assertIs(n, None)

        n = self.mf.find_node('.mod2.*')
        self.assertIsInstance(n, modulegraph.InvalidRelativeImport)

    def test_subpkg_bad_import(self):
        self.mf.import_hook('pkg.sub')

        n = self.mf.find_node('toplevel')
        self.assertIs(n, None)

        n = self.mf.find_node('pkg.mod1')
        self.assertIsInstance(n, modulegraph.SourceModule)

        n = self.mf.find_node('pkg.mod3')
        self.assertIsInstance(n, modulegraph.SourceModule)

if __name__ == "__main__":
    unittest.main()
