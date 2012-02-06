from unittest2.test.support import LoggingResult

import unittest2


class Test_TestSkipping(unittest2.TestCase):

    def test_skipping(self):
        class Foo(unittest2.TestCase):
            def test_skip_me(self):
                self.skipTest("skip")
        events = []
        result = LoggingResult(events)
        test = Foo("test_skip_me")
        test.run(result)
        self.assertEqual(events, ['startTest', 'addSkip', 'stopTest'])
        self.assertEqual(result.skipped, [(test, "skip")])

        # Try letting setUp skip the test now.
        class Foo(unittest2.TestCase):
            def setUp(self):
                self.skipTest("testing")
            def test_nothing(self): pass
        events = []
        result = LoggingResult(events)
        test = Foo("test_nothing")
        test.run(result)
        self.assertEqual(events, ['startTest', 'addSkip', 'stopTest'])
        self.assertEqual(result.skipped, [(test, "testing")])
        self.assertEqual(result.testsRun, 1)

    def test_skipping_decorators(self):
        op_table = ((unittest2.skipUnless, False, True),
                    (unittest2.skipIf, True, False))
        for deco, do_skip, dont_skip in op_table:
            class Foo(unittest2.TestCase):
                def test_skip(self): 
                    pass
                test_skip = deco(do_skip, "testing")(test_skip)

                def test_dont_skip(self): 
                    pass
                test_dont_skip = deco(dont_skip, "testing")(test_dont_skip)
            
            test_do_skip = Foo("test_skip")
            test_dont_skip = Foo("test_dont_skip")
            suite = unittest2.TestSuite([test_do_skip, test_dont_skip])
            events = []
            result = LoggingResult(events)
            suite.run(result)
            self.assertEqual(len(result.skipped), 1)
            expected = ['startTest', 'addSkip', 'stopTest',
                        'startTest', 'addSuccess', 'stopTest']
            self.assertEqual(events, expected)
            self.assertEqual(result.testsRun, 2)
            self.assertEqual(result.skipped, [(test_do_skip, "testing")])
            self.assertTrue(result.wasSuccessful())
        
    def test_skip_class(self):
        class Foo(unittest2.TestCase):
            def test_1(self):
                record.append(1)
        
        # was originally a class decorator...
        Foo = unittest2.skip("testing")(Foo)
        record = []
        result = unittest2.TestResult()
        test = Foo("test_1")
        suite = unittest2.TestSuite([test])
        suite.run(result)
        self.assertEqual(result.skipped, [(test, "testing")])
        self.assertEqual(record, [])

    def test_expected_failure(self):
        class Foo(unittest2.TestCase):
            def test_die(self):
                self.fail("help me!")
            test_die = unittest2.expectedFailure(test_die)
        events = []
        result = LoggingResult(events)
        test = Foo("test_die")
        test.run(result)
        self.assertEqual(events,
                         ['startTest', 'addExpectedFailure', 'stopTest'])
        self.assertEqual(result.expectedFailures[0][0], test)
        self.assertTrue(result.wasSuccessful())

    def test_unexpected_success(self):
        class Foo(unittest2.TestCase):
            def test_die(self):
                pass
            test_die = unittest2.expectedFailure(test_die)
        events = []
        result = LoggingResult(events)
        test = Foo("test_die")
        test.run(result)
        self.assertEqual(events,
                         ['startTest', 'addUnexpectedSuccess', 'stopTest'])
        self.assertFalse(result.failures)
        self.assertEqual(result.unexpectedSuccesses, [test])
        self.assertTrue(result.wasSuccessful())

    def test_skip_doesnt_run_setup(self):
        class Foo(unittest2.TestCase):
            wasSetUp = False
            wasTornDown = False
            def setUp(self):
                Foo.wasSetUp = True
            def tornDown(self):
                Foo.wasTornDown = True
            def test_1(self):
                pass
            test_1 = unittest2.skip('testing')(test_1)
        
        result = unittest2.TestResult()
        test = Foo("test_1")
        suite = unittest2.TestSuite([test])
        suite.run(result)
        self.assertEqual(result.skipped, [(test, "testing")])
        self.assertFalse(Foo.wasSetUp)
        self.assertFalse(Foo.wasTornDown)
    
    def test_decorated_skip(self):
        def decorator(func):
            def inner(*a):
                return func(*a)
            return inner
        
        class Foo(unittest2.TestCase):
            def test_1(self):
                pass
            test_1 = decorator(unittest2.skip('testing')(test_1))
        
        result = unittest2.TestResult()
        test = Foo("test_1")
        suite = unittest2.TestSuite([test])
        suite.run(result)
        self.assertEqual(result.skipped, [(test, "testing")])


if __name__ == '__main__':
    unittest2.main()
