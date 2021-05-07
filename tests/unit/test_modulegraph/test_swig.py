"""
Test importability of SWIG-generated C extensions.
"""
import os
import sys
from PyInstaller.lib.modulegraph import modulegraph

if sys.version_info[:2] <= (2,6):
    import unittest2 as unittest
else:
    import unittest

class TestSWIGImportability(unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, value, types):
            if not isinstance(value, types):
                self.fail("%r is not an instance of %r"%(value, types))

    def test_swig_importability(self):
        # Absolute path of the top-level data directory for this unit test.
        test_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'testpkg-swig')

        # Mock module graph relative to this directory.
        module_graph = modulegraph.ModuleGraph(path=[ test_dir ] + sys.path)

        # Graph node corresponding to a mock SWIG module.
        swig_module = module_graph._safe_import_hook(
            'pkg.sample', source_module=None, target_attr_names=())[0]
        self.assertIsInstance(swig_module, modulegraph.SourceModule)

        # Graph node corresponding to a mock SWIG C extension imported by the
        # prior module. While this should technically be a C extension rather
        # than a module, reliably testing the latter in a cross-platform manner
        # is both non-trivial and gains us relatively little over this approach.
        swig_c_extension = module_graph.find_node('pkg._sample')
        self.assertIsInstance(swig_c_extension, modulegraph.SourceModule)

if __name__ == "__main__":
    unittest.main()
