import os
import sys
if sys.version_info[:2] <= (2,6):
    import unittest2 as unittest
else:
    import unittest

from PyInstaller.lib.modulegraph import modulegraph


# XXX: Todo: simular tests with bytecompiled modules


class TestEdgeData (unittest.TestCase):
    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, value, types):
            if not isinstance(value, types):
                self.fail("%r is not an instance of %r"%(value, types))

    def test_regular_import(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-edgedata')
        mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        script_name = os.path.join(root, 'script.py')
        mf.add_script(script_name)

        script_node = mf.find_node(script_name)
        self.assertIsInstance(script_node, modulegraph.Script)


        node = mf.find_node('toplevel_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=False, fromlist=False))

        node = mf.find_node('toplevel_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=False, fromlist=False))

        node = mf.find_node('toplevel_class_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=False, fromlist=False))

        node = mf.find_node('toplevel_class_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=False, fromlist=False))

        node = mf.find_node('toplevel_conditional_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=False, tryexcept=False, fromlist=False))

        node = mf.find_node('toplevel_conditional_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=False, tryexcept=False, fromlist=False))

        node = mf.find_node('toplevel_conditional_import_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=False, tryexcept=True, fromlist=False))

        node = mf.find_node('toplevel_conditional_import_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=False, tryexcept=True, fromlist=False))

        node = mf.find_node('toplevel_conditional_import2_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=False, tryexcept=True, fromlist=False))

        node = mf.find_node('toplevel_conditional_import2_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=False, tryexcept=True, fromlist=False))

        node = mf.find_node('toplevel_import_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=True, fromlist=False))

        node = mf.find_node('toplevel_import_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=True, fromlist=False))

        node = mf.find_node('toplevel_import2_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=True, fromlist=False))

        node = mf.find_node('toplevel_import2_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=True, fromlist=False))

        node = mf.find_node('function_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=False, fromlist=False))

        node = mf.find_node('function_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=False, fromlist=False))

        node = mf.find_node('function_class_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=False, fromlist=False))

        node = mf.find_node('function_class_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=False, fromlist=False))

        node = mf.find_node('function_conditional_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=False, fromlist=False))

        node = mf.find_node('function_conditional_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=False, fromlist=False))

        node = mf.find_node('function_conditional_import_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=True, fromlist=False))

        node = mf.find_node('function_conditional_import_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=True, fromlist=False))

        node = mf.find_node('function_conditional_import2_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=True, fromlist=False))

        node = mf.find_node('function_conditional_import2_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=True, fromlist=False))

        node = mf.find_node('function_import_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=True, fromlist=False))

        node = mf.find_node('function_import_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=True, fromlist=False))

        node = mf.find_node('function_import2_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=True, fromlist=False))

        node = mf.find_node('function_import2_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=True, fromlist=False))


    def test_multi_import(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-edgedata')
        mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        script_name = os.path.join(root, 'script_multi_import.py')
        mf.add_script(script_name)

        script_node = mf.find_node(script_name)
        self.assertIsInstance(script_node, modulegraph.Script)

        # FIXME PyInstaller: original _load_tail returned a MissingModule if
        # (_save)_import_module did return None. PyInstaller changed this in
        # cae47e4f5b51a94ac3ceb5d093283ba0cc895589 and raises an ImportError.
        # Thus the MissingModule node (which was expected to be created when
        # scanning the script above) doesn't exist and findNode will return
        # None, which makes this test fail.
        #node = mf.find_node('os.path')
        #ed = mf.edgeData(script_node, node)
        #self.assertIsInstance(ed, modulegraph.DependencyInfo)
        #self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=True, fromlist=False))

        node = mf.find_node('os')
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=False, fromlist=False))

        node = mf.find_node('sys')
        ed = mf.edgeData(script_node, node)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=False, fromlist=False))

        node = mf.find_node('platform')
        ed = mf.edgeData(script_node, node)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=False, fromlist=False))

        node = mf.find_node('email')
        ed = mf.edgeData(script_node, node)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=False, fromlist=False))

    def test_from_imports(self):
        root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'testpkg-edgedata')
        mf = modulegraph.ModuleGraph(path=[ root ] + sys.path)
        script_name = os.path.join(root, 'script_from_import.py')
        mf.add_script(script_name)

        script_node = mf.find_node(script_name)
        self.assertIsInstance(script_node, modulegraph.Script)


        node = mf.find_node('pkg.toplevel_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=False, fromlist=True))

        node = mf.find_node('pkg.toplevel_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=False, fromlist=True))

        node = mf.find_node('pkg.toplevel_class_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=False, fromlist=True))

        node = mf.find_node('pkg.toplevel_class_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=False, fromlist=True))

        node = mf.find_node('pkg.toplevel_conditional_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=False, tryexcept=False, fromlist=True))

        node = mf.find_node('pkg.toplevel_conditional_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=False, tryexcept=False, fromlist=True))

        node = mf.find_node('pkg.toplevel_conditional_import_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=False, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.toplevel_conditional_import_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=False, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.toplevel_conditional_import2_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=False, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.toplevel_conditional_import2_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=False, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.toplevel_import_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.toplevel_import_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.toplevel_import2_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.toplevel_import2_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=False, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.function_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=False, fromlist=True))

        node = mf.find_node('pkg.function_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=False, fromlist=True))

        node = mf.find_node('pkg.function_class_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=False, fromlist=True))

        node = mf.find_node('pkg.function_class_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=False, fromlist=True))

        node = mf.find_node('pkg.function_conditional_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=False, fromlist=True))

        node = mf.find_node('pkg.function_conditional_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=False, fromlist=True))

        node = mf.find_node('pkg.function_conditional_import_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.function_conditional_import_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.function_conditional_import2_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.function_conditional_import2_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=True, function=True, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.function_import_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.function_import_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.function_import2_existing')
        self.assertIsInstance(node, modulegraph.SourceModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=True, fromlist=True))

        node = mf.find_node('pkg.function_import2_nonexisting')
        self.assertIsInstance(node, modulegraph.MissingModule)
        ed = mf.edgeData(script_node, node)
        self.assertIsInstance(ed, modulegraph.DependencyInfo)
        self.assertEqual(ed, modulegraph.DependencyInfo(conditional=False, function=True, tryexcept=True, fromlist=True))


if __name__ == "__main__":
    unittest.main()
