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

    def test_compat(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-compatmodule')
        mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        mf.import_hook('pkg.api')

        node = mf.find_node('pkg')
        self.assertIsInstance(node, modulegraph.Package)

        node = mf.find_node('pkg.api')
        self.assertIsInstance(node, modulegraph.SourceModule)

        if sys.version_info[0] == 2:
            node = mf.find_node('pkg.api2')
            self.assertIsInstance(node, modulegraph.SourceModule)

            node = mf.find_node('pkg.api3')
            self.assertIsInstance(node, modulegraph.InvalidSourceModule)

            node = mf.find_node('http.client')
            self.assertIs(node, None)

            node = mf.find_node('urllib2')
            self.assertIsInstance(node, modulegraph.SourceModule)

        else:
            node = mf.find_node('pkg.api2')
            self.assertIsInstance(node, modulegraph.InvalidSourceModule)

            node = mf.find_node('pkg.api3')
            self.assertIsInstance(node, modulegraph.SourceModule)

            node = mf.find_node('http.client')
            self.assertIsInstance(node, modulegraph.SourceModule)

            node = mf.find_node('urllib2')
            self.assertIs(node, None)




if __name__ == "__main__":
    unittest.main()
