
import sys

import unittest2
from unittest2.test.support import OldTestResult, catch_warnings

import warnings
# needed to enable the deprecation warnings
warnings.simplefilter('default')

class TestWith(unittest2.TestCase):
    """Tests that use the with statement live in this
    module so that all other tests can be run with Python 2.4.
    """

    def runContext(self, ctxobj, func, *funcargs, **funckwargs):
        bound_to = ctxobj.__enter__()
        try:
            func(bound_to, *funcargs, **funckwargs)
        except Exception, e:
            if not ctxobj.__exit__(*sys.exc_info()):
                raise
        else:
            ctxobj.__exit__(None, None, None)

    def testAssertRaisesExcValue(self):
        class ExceptionMock(Exception):
            pass

        def Stub(foo):
            raise ExceptionMock(foo)
        v = "particular value"

        ctx = self.assertRaises(ExceptionMock)
        self.runContext(ctx, lambda cm: Stub(v))
        e = ctx.exception
        self.assertIsInstance(e, ExceptionMock)
        self.assertEqual(e.args[0], v)

    def test_assert_dict_unicode_error(self):
        def run(cm):
            # This causes a UnicodeWarning due to its craziness
            one = ''.join([chr(i) for i in range(255)])
            # this used to cause a UnicodeDecodeError constructing the failure msg
            ar_cm = self.assertRaises(self.failureException)
            innerrun =lambda x: self.assertDictContainsSubset({'foo': one}, {'foo': u'\uFFFD'})
            self.runContext(ar_cm, innerrun)
        cm = catch_warnings(record=True)
        self.runContext(cm, run)

    def test_formatMessage_unicode_error(self):
        def run(cm):
            # This causes a UnicodeWarning due to its craziness
            one = ''.join([chr(i) for i in range(255)])
            # this used to cause a UnicodeDecodeError constructing msg
            self._formatMessage(one, u'\uFFFD')        
        cm = catch_warnings(record=True)
        self.runContext(cm, run)

    def assertOldResultWarning(self, test, failures):
        def run(log):
            result = OldTestResult()
            test.run(result)
            self.assertEqual(len(result.failures), failures)
            warning, = log
            self.assertIs(warning.category, DeprecationWarning)
        cm = catch_warnings(record=True)
        self.runContext(cm, run)

    def test_old_testresult(self):
        class Test(unittest2.TestCase):
            def testSkip(self):
                self.skipTest('foobar')
            def testExpectedFail(self):
                raise TypeError
            testExpectedFail = unittest2.expectedFailure(testExpectedFail)
            def testUnexpectedSuccess(self):
                pass
            testUnexpectedSuccess = unittest2.expectedFailure(testUnexpectedSuccess)
        
        for test_name, should_pass in (('testSkip', True), 
                                       ('testExpectedFail', True), 
                                       ('testUnexpectedSuccess', False)):
            test = Test(test_name)
            self.assertOldResultWarning(test, int(not should_pass))
        
    def test_old_testresult_setup(self):
        class Test(unittest2.TestCase):
            def setUp(self):
                self.skipTest('no reason')
            def testFoo(self):
                pass
        self.assertOldResultWarning(Test('testFoo'), 0)
        
    def test_old_testresult_class(self):
        class Test(unittest2.TestCase):
            def testFoo(self):
                pass
        Test = unittest2.skip('no reason')(Test)
        self.assertOldResultWarning(Test('testFoo'), 0)

    def testPendingDeprecationMethodNames(self):
        """Test fail* methods pending deprecation, they will warn in 3.2.

        Do not use these methods.  They will go away in 3.3.
        """
        def run(cm):
            self.failIfEqual(3, 5)
            self.failUnlessEqual(3, 3)
            self.failUnlessAlmostEqual(2.0, 2.0)
            self.failIfAlmostEqual(3.0, 5.0)
            self.failUnless(True)
            self.failUnlessRaises(TypeError, lambda _: 3.14 + u'spam')
            self.failIf(False)
        cm = catch_warnings(record=True)
        self.runContext(cm,run)

    def testAssertDictContainsSubset_UnicodeVsStrValues(self):
        def run(cm):
            one = ''.join([chr(i) for i in range(255)])
            two = u'\uFFFD'
            # this used to cause a UnicodeDecodeError when the values were compared under python 2.3, under
            # python 2.6 it causes a UnicodeWarning so wrapping in catch_warnings context manager
            self.assertRaises(self.failureException, self.assertDictContainsSubset, {'foo': one}, {'foo': two})
        cm = catch_warnings(record=True)
        self.runContext(cm, run)


if __name__ == '__main__':
    unittest2.main()
