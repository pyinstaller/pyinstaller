import sys

from cStringIO import StringIO

import unittest2
from unittest2.test.support import resultFactory


class TestSetups(unittest2.TestCase):
    
    def getRunner(self):
        return unittest2.TextTestRunner(resultclass=resultFactory,
                                          stream=StringIO())
    def runTests(self, *cases):
        suite = unittest2.TestSuite()
        for case in cases:
            tests = unittest2.defaultTestLoader.loadTestsFromTestCase(case)
            suite.addTests(tests)
        
        runner = self.getRunner()
        
        # creating a nested suite exposes some potential bugs
        realSuite = unittest2.TestSuite()
        realSuite.addTest(suite)
        # adding empty suites to the end exposes potential bugs
        suite.addTest(unittest2.TestSuite())
        realSuite.addTest(unittest2.TestSuite())
        return runner.run(realSuite)
    
    def test_setup_class(self):
        class Test(unittest2.TestCase):
            setUpCalled = 0
            def setUpClass(cls):
                Test.setUpCalled += 1
                unittest2.TestCase.setUpClass()
            setUpClass = classmethod(setUpClass)
            def test_one(self):
                pass
            def test_two(self):
                pass
            
        result = self.runTests(Test)
        
        self.assertEqual(Test.setUpCalled, 1)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 0)

    def test_teardown_class(self):
        class Test(unittest2.TestCase):
            tearDownCalled = 0
            def tearDownClass(cls):
                Test.tearDownCalled += 1
                unittest2.TestCase.tearDownClass()
            tearDownClass = classmethod(tearDownClass)
            def test_one(self):
                pass
            def test_two(self):
                pass
            
        result = self.runTests(Test)
        
        self.assertEqual(Test.tearDownCalled, 1)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 0)
    
    def test_teardown_class_two_classes(self):
        class Test(unittest2.TestCase):
            tearDownCalled = 0
            def tearDownClass(cls):
                Test.tearDownCalled += 1
                unittest2.TestCase.tearDownClass()
            tearDownClass = classmethod(tearDownClass)
            def test_one(self):
                pass
            def test_two(self):
                pass
            
        class Test2(unittest2.TestCase):
            tearDownCalled = 0
            def tearDownClass(cls):
                Test2.tearDownCalled += 1
                unittest2.TestCase.tearDownClass()
            tearDownClass = classmethod(tearDownClass)
            def test_one(self):
                pass
            def test_two(self):
                pass
        
        result = self.runTests(Test, Test2)
        
        self.assertEqual(Test.tearDownCalled, 1)
        self.assertEqual(Test2.tearDownCalled, 1)
        self.assertEqual(result.testsRun, 4)
        self.assertEqual(len(result.errors), 0)

    def test_error_in_setupclass(self):
        class BrokenTest(unittest2.TestCase):
            def setUpClass(cls):
                raise TypeError('foo')
            setUpClass = classmethod(setUpClass)
            def test_one(self):
                pass
            def test_two(self):
                pass
        
        result = self.runTests(BrokenTest)
        
        self.assertEqual(result.testsRun, 0)
        self.assertEqual(len(result.errors), 1)
        error, _ = result.errors[0]
        self.assertEqual(str(error), 
                    'setUpClass (%s.BrokenTest)' % __name__)

    def test_error_in_teardown_class(self):
        class Test(unittest2.TestCase):
            tornDown = 0
            def tearDownClass(cls):
                Test.tornDown += 1
                raise TypeError('foo')
            tearDownClass = classmethod(tearDownClass)
            def test_one(self):
                pass
            def test_two(self):
                pass
            
        class Test2(unittest2.TestCase):
            tornDown = 0
            def tearDownClass(cls):
                Test2.tornDown += 1
                raise TypeError('foo')
            tearDownClass = classmethod(tearDownClass)
            def test_one(self):
                pass
            def test_two(self):
                pass
        
        result = self.runTests(Test, Test2)
        self.assertEqual(result.testsRun, 4)
        self.assertEqual(len(result.errors), 2)
        self.assertEqual(Test.tornDown, 1)
        self.assertEqual(Test2.tornDown, 1)
        
        error, _ = result.errors[0]
        self.assertEqual(str(error), 
                    'tearDownClass (%s.Test)' % __name__)

    def test_class_not_torndown_when_setup_fails(self):
        class Test(unittest2.TestCase):
            tornDown = False
            def setUpClass(cls):
                raise TypeError
            setUpClass = classmethod(setUpClass)
            def tearDownClass(cls):
                Test.tornDown = True
                raise TypeError('foo')
            tearDownClass = classmethod(tearDownClass)
            def test_one(self):
                pass

        self.runTests(Test)
        self.assertFalse(Test.tornDown)
    
    def test_class_not_setup_or_torndown_when_skipped(self):
        class Test(unittest2.TestCase):
            classSetUp = False
            tornDown = False
            def setUpClass(cls):
                Test.classSetUp = True
            setUpClass = classmethod(setUpClass)
            def tearDownClass(cls):
                Test.tornDown = True
            tearDownClass = classmethod(tearDownClass)
            def test_one(self):
                pass

        Test = unittest2.skip("hop")(Test)
        self.runTests(Test)
        self.assertFalse(Test.classSetUp)
        self.assertFalse(Test.tornDown)

    def test_setup_teardown_order_with_pathological_suite(self):
        results = []
        
        class Module1(object):
            def setUpModule():
                results.append('Module1.setUpModule')
            setUpModule = staticmethod(setUpModule)
            def tearDownModule():
                results.append('Module1.tearDownModule')
            tearDownModule = staticmethod(tearDownModule)
    
        class Module2(object):
            def setUpModule():
                results.append('Module2.setUpModule')
            setUpModule = staticmethod(setUpModule)
            def tearDownModule():
                results.append('Module2.tearDownModule')
            tearDownModule = staticmethod(tearDownModule)
                
        class Test1(unittest2.TestCase):
            def setUpClass(cls):
                results.append('setup 1')
            setUpClass = classmethod(setUpClass)
            def tearDownClass(cls):
                results.append('teardown 1')
            tearDownClass = classmethod(tearDownClass)
            def testOne(self):
                results.append('Test1.testOne')
            def testTwo(self):
                results.append('Test1.testTwo')
            
        class Test2(unittest2.TestCase):
            def setUpClass(cls):
                results.append('setup 2')
            setUpClass = classmethod(setUpClass)
            def tearDownClass(cls):
                results.append('teardown 2')
            tearDownClass = classmethod(tearDownClass)
            def testOne(self):
                results.append('Test2.testOne')
            def testTwo(self):
                results.append('Test2.testTwo')
            
        class Test3(unittest2.TestCase):
            def setUpClass(cls):
                results.append('setup 3')
            setUpClass = classmethod(setUpClass)
            def tearDownClass(cls):
                results.append('teardown 3')
            tearDownClass = classmethod(tearDownClass)
            def testOne(self):
                results.append('Test3.testOne')
            def testTwo(self):
                results.append('Test3.testTwo')
        
        Test1.__module__ = Test2.__module__ = 'Module'
        Test3.__module__ = 'Module2'
        sys.modules['Module'] = Module1
        sys.modules['Module2'] = Module2
        
        first = unittest2.TestSuite((Test1('testOne'),))
        second = unittest2.TestSuite((Test1('testTwo'),))
        third = unittest2.TestSuite((Test2('testOne'),))
        fourth = unittest2.TestSuite((Test2('testTwo'),))
        fifth = unittest2.TestSuite((Test3('testOne'),))
        sixth = unittest2.TestSuite((Test3('testTwo'),))
        suite = unittest2.TestSuite((first, second, third, fourth, fifth, sixth))
        
        runner = self.getRunner()
        result = runner.run(suite)
        self.assertEqual(result.testsRun, 6)
        self.assertEqual(len(result.errors), 0)

        self.assertEqual(results,
                         ['Module1.setUpModule', 'setup 1', 
                          'Test1.testOne', 'Test1.testTwo', 'teardown 1',
                          'setup 2', 'Test2.testOne', 'Test2.testTwo', 
                          'teardown 2', 'Module1.tearDownModule',
                          'Module2.setUpModule', 'setup 3',
                          'Test3.testOne', 'Test3.testTwo', 
                          'teardown 3', 'Module2.tearDownModule'])
        
    def test_setup_module(self):
        class Module(object):
            moduleSetup = 0
            def setUpModule():
                Module.moduleSetup += 1
            setUpModule = staticmethod(setUpModule)
        
        class Test(unittest2.TestCase):
            def test_one(self):
                pass
            def test_two(self):
                pass
        Test.__module__ = 'Module'
        sys.modules['Module'] = Module
        
        result = self.runTests(Test)
        self.assertEqual(Module.moduleSetup, 1)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 0)
    
    def test_error_in_setup_module(self):
        class Module(object):
            moduleSetup = 0
            moduleTornDown = 0
            def setUpModule():
                Module.moduleSetup += 1
                raise TypeError('foo')
            setUpModule = staticmethod(setUpModule)
            def tearDownModule():
                Module.moduleTornDown += 1
            tearDownModule = staticmethod(tearDownModule)
        
        class Test(unittest2.TestCase):
            classSetUp = False
            classTornDown = False
            def setUpClass(cls):
                Test.classSetUp = True
            setUpClass = classmethod(setUpClass)
            def tearDownClass(cls):
                Test.classTornDown = True
            tearDownClass = classmethod(tearDownClass)
            def test_one(self):
                pass
            def test_two(self):
                pass
        
        class Test2(unittest2.TestCase):
            def test_one(self):
                pass
            def test_two(self):
                pass
        Test.__module__ = 'Module'
        Test2.__module__ = 'Module'
        sys.modules['Module'] = Module
        
        result = self.runTests(Test, Test2)
        self.assertEqual(Module.moduleSetup, 1)
        self.assertEqual(Module.moduleTornDown, 0)
        self.assertEqual(result.testsRun, 0)
        self.assertFalse(Test.classSetUp)
        self.assertFalse(Test.classTornDown)
        self.assertEqual(len(result.errors), 1)
        error, _ = result.errors[0]
        self.assertEqual(str(error), 'setUpModule (Module)')
        
    def test_testcase_with_missing_module(self):
        class Test(unittest2.TestCase):
            def test_one(self):
                pass
            def test_two(self):
                pass
        Test.__module__ = 'Module'
        sys.modules.pop('Module', None)
        
        result = self.runTests(Test)
        self.assertEqual(result.testsRun, 2)

    def test_teardown_module(self):
        class Module(object):
            moduleTornDown = 0
            def tearDownModule():
                Module.moduleTornDown += 1
            tearDownModule = staticmethod(tearDownModule)
        
        class Test(unittest2.TestCase):
            def test_one(self):
                pass
            def test_two(self):
                pass
        Test.__module__ = 'Module'
        sys.modules['Module'] = Module
        
        result = self.runTests(Test)
        self.assertEqual(Module.moduleTornDown, 1)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 0)

    def test_error_in_teardown_module(self):
        class Module(object):
            moduleTornDown = 0
            def tearDownModule():
                Module.moduleTornDown += 1
                raise TypeError('foo')
            tearDownModule = staticmethod(tearDownModule)
        
        class Test(unittest2.TestCase):
            classSetUp = False
            classTornDown = False
            def setUpClass(cls):
                Test.classSetUp = True
            setUpClass = classmethod(setUpClass)
            def tearDownClass(cls):
                Test.classTornDown = True
            tearDownClass = classmethod(tearDownClass)
            def test_one(self):
                pass
            def test_two(self):
                pass
        
        class Test2(unittest2.TestCase):
            def test_one(self):
                pass
            def test_two(self):
                pass
        Test.__module__ = 'Module'
        Test2.__module__ = 'Module'
        sys.modules['Module'] = Module
        
        result = self.runTests(Test, Test2)
        self.assertEqual(Module.moduleTornDown, 1)
        self.assertEqual(result.testsRun, 4)
        self.assertTrue(Test.classSetUp)
        self.assertTrue(Test.classTornDown)
        self.assertEqual(len(result.errors), 1)
        error, _ = result.errors[0]
        self.assertEqual(str(error), 'tearDownModule (Module)')

    def test_skiptest_in_setupclass(self):
        class Test(unittest2.TestCase):
            def setUpClass(cls):
                raise unittest2.SkipTest('foo')
            setUpClass = classmethod(setUpClass)
            def test_one(self):
                pass
            def test_two(self):
                pass

        result = self.runTests(Test)
        self.assertEqual(result.testsRun, 0)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.skipped), 1)
        skipped = result.skipped[0][0]
        self.assertEqual(str(skipped), 'setUpClass (%s.Test)' % __name__)

    def test_skiptest_in_setupmodule(self):
        class Test(unittest2.TestCase):
            def test_one(self):
                pass
            def test_two(self):
                pass

        class Module(object):
            def setUpModule():
                raise unittest2.SkipTest('foo')
            setUpModule = staticmethod(setUpModule)

        Test.__module__ = 'Module'
        sys.modules['Module'] = Module

        result = self.runTests(Test)
        self.assertEqual(result.testsRun, 0)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.skipped), 1)
        skipped = result.skipped[0][0]
        self.assertEqual(str(skipped), 'setUpModule (Module)')

    def test_suite_debug_executes_setups_and_teardowns(self):
        ordering = []

        class Module(object):
            def setUpModule():
                ordering.append('setUpModule')
            setUpModule = staticmethod(setUpModule)
            def tearDownModule():
                ordering.append('tearDownModule')
            tearDownModule = staticmethod(tearDownModule)

        class Test(unittest2.TestCase):
            def setUpClass(cls):
                ordering.append('setUpClass')
            setUpClass = classmethod(setUpClass)
            def tearDownClass(cls):
                ordering.append('tearDownClass')
            tearDownClass = classmethod(tearDownClass)
            def test_something(self):
                ordering.append('test_something')

        Test.__module__ = 'Module'
        sys.modules['Module'] = Module

        suite = unittest2.defaultTestLoader.loadTestsFromTestCase(Test)
        suite.debug()
        expectedOrder = ['setUpModule', 'setUpClass', 'test_something', 'tearDownClass', 'tearDownModule']
        self.assertEqual(ordering, expectedOrder)

    def test_suite_debug_propagates_exceptions(self):
        class Module(object):
            def setUpModule():
                if phase == 0:
                    raise Exception('setUpModule')
            setUpModule = staticmethod(setUpModule)
            def tearDownModule():
                if phase == 1:
                    raise Exception('tearDownModule')
            tearDownModule = staticmethod(tearDownModule)

        class Test(unittest2.TestCase):
            def setUpClass(cls):
                if phase == 2:
                    raise Exception('setUpClass')
            setUpClass = classmethod(setUpClass)
            def tearDownClass(cls):
                if phase == 3:
                    raise Exception('tearDownClass')
            tearDownClass = classmethod(tearDownClass)
            def test_something(self):
                if phase == 4:
                    raise Exception('test_something')

        Test.__module__ = 'Module'
        sys.modules['Module'] = Module

        _suite = unittest2.defaultTestLoader.loadTestsFromTestCase(Test)
        suite = unittest2.TestSuite()
        
        # nesting a suite again exposes a bug in the initial implementation
        suite.addTest(_suite)
        messages = ('setUpModule', 'tearDownModule', 'setUpClass', 'tearDownClass', 'test_something')
        for phase, msg in enumerate(messages):
            self.assertRaisesRegexp(Exception, msg, suite.debug)
