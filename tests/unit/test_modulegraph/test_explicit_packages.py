import unittest

import os
import sys

from PyInstaller.lib.modulegraph import find_modules
from PyInstaller.lib.modulegraph import modulegraph


class PackagesTestCase (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, object, types, message=None):
            self.assertTrue(isinstance(object, types),
                    message or '%r is not an instance of %r'%(object, types))

    def testIncludePackage(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-packages')

        mf = find_modules.find_modules(
                path=[root]+sys.path,
                scripts=[os.path.join(root, "main_script.py")],
                packages=['pkg'],
                debug=1)

        node = mf.find_node('pkg')
        self.assertIsInstance(node, modulegraph.Package)

        node = mf.find_node('pkg.sub3')
        self.assertIsInstance(node, modulegraph.SourceModule)

    def testIncludePackageWithExclude(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-packages')

        mf = find_modules.find_modules(
                path=[root]+sys.path,
                scripts=[os.path.join(root, "main_script.py")],
                packages=['pkg'],
                excludes=['pkg.sub3'])

        node = mf.find_node('pkg')
        self.assertIsInstance(node, modulegraph.Package)

        node = mf.find_node('pkg.sub3')
        self.assertIsInstance(node, modulegraph.ExcludedModule)

if __name__ == '__main__':
    unittest.main()
