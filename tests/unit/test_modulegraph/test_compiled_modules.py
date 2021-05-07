import unittest

import os, py_compile, sys

from PyInstaller.lib.modulegraph import modulegraph

class CompiledModuleTests(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.join(
                os.path.dirname(__file__),
                'testpkg-compiled')
        self.compiled_dir = os.path.join(
                self.base_dir, 'compiled')
        self.source_dir = os.path.join(
                self.base_dir, 'source')

        for fn in os.listdir(self.source_dir):
            if not fn.endswith('.py'): continue

            py_compile.compile(
                os.path.join(self.source_dir, fn),
                os.path.join(self.compiled_dir, fn + 'c'))

    def tearDown(self):
        for fn in os.listdir(self.compiled_dir):
            if fn.endswith('.pyc'):
                os.unlink(os.path.join(self.compiled_dir, fn))

    def testCompiledModules(self):
        mf = modulegraph.ModuleGraph(path=[self.compiled_dir] + sys.path)
        #self.mf.debug = 999
        mf.add_script(os.path.join(self.compiled_dir, 'script.py'))

        o = mf.find_node('mod1')
        self.assertIsInstance(o, modulegraph.CompiledModule)
        self.assertEqual(o._global_attr_names, { 'mod2', 'mod3', 'foo' })
        self.assertEqual(o._starimported_ignored_module_names, set())

        o = mf.find_node('mod2')
        self.assertIsInstance(o, modulegraph.CompiledModule)
        self.assertEqual(o._global_attr_names,
                         { 'mod1', 'sys', 'testme', 'bar' })
        self.assertEqual(o._starimported_ignored_module_names, set())

        o = mf.find_node('mod3')
        self.assertIsInstance(o, modulegraph.CompiledModule)
        self.assertEqual(o._global_attr_names, { 'os', 'path'})
        self.assertEqual(o._starimported_ignored_module_names, set())

        o = mf.find_node('mod4')
        other = mf.find_node('zipfile')
        self.assertIsInstance(o, modulegraph.CompiledModule)
        self.assertEqual(o._global_attr_names, other._global_attr_names)
        self.assertEqual(o._starimported_ignored_module_names, {'math'})

        o = mf.find_node('mod5')
        self.assertIs(o, None)


if __name__ == '__main__':
    #import profile
    #profile.run('unittest.main()', sort=2)
    unittest.main()
