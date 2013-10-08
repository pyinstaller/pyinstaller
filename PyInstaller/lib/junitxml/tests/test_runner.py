"""Test XmlTestRunner functionality for junitxml.

:Author: Duncan Findlay <duncan@duncf.ca>
"""
import xml.dom.minidom
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import junitxml.runner


# Old versions of unittest don't have these "fancy" types of results.
_FANCY_UNITTEST = (hasattr(unittest, 'skip') and
                   hasattr(unittest, 'expectedFailure'))


class TestXMLTestRunner(unittest.TestCase):

    class DummyTestCase(unittest.TestCase):

        def test_pass(self):
            pass

        def test_fail(self):
            self.fail()

        def test_error(self):
            raise Exception()

        if _FANCY_UNITTEST:

            @unittest.skip('skipped')
            def test_skip(self):
                pass

            @unittest.expectedFailure
            def test_xfail(self):
                self.fail('all is good')

            @unittest.expectedFailure
            def test_unexpected_success(self):
                pass

    def _run_runner(self, test_suite):
        xml_out = StringIO()
        console = StringIO()

        runner = junitxml.runner.JUnitXmlTestRunner(
            xml_stream=xml_out, txt_stream=console)
        result = runner.run(test_suite)

        return (result, xml_out, console)

    def test_xml_output(self):
        """Tests that runner properly gives XML output."""
        test_suite = unittest.TestLoader().loadTestsFromTestCase(
            self.DummyTestCase)

        result, xml_out, console = self._run_runner(test_suite)

        num_tests = test_suite.countTestCases()

        # Make sure the XML output looks correct.
        value = xml_out.getvalue()
        document = xml.dom.minidom.parseString(value)

        self.assertEqual(document.documentElement.tagName, 'testsuite')
        self.assertEqual(document.documentElement.getAttribute('tests'),
                         str(num_tests))

    def test_console_output_fail(self):
        """Tests that failure is reported properly on stderr."""
        test_suite = unittest.TestLoader().loadTestsFromTestCase(
            self.DummyTestCase)

        result, xml_out, console = self._run_runner(test_suite)

        num_tests = test_suite.countTestCases()

        # Make sure the console output looks correct.
        value = console.getvalue()
        self.assertTrue('Ran %d tests in ' % (num_tests,) in value,
                        'Output was:\n%s' % (value,))
        self.assertTrue('FAILED (failures=1' in value,
                        'Output was:\n%s' % (value,))
        self.assertTrue('errors=1' in value,
                        'Output was:\n%s' % (value,))

        if _FANCY_UNITTEST:
            self.assertTrue('expected failures=1' in value,
                            'Output was:\n%s' % (value,))
            self.assertTrue('skipped=1' in value,
                            'Output was:\n%s' % (value,))
            self.assertTrue('unexpected successes=1' in value,
                            'Output was:\n%s' % (value,))

    def test_console_output_ok(self):
        """Tests that success is reported properly on stderr."""
        test_suite = unittest.TestSuite()
        test_suite.addTest(self.DummyTestCase('test_pass'))

        result, xml_out, console = self._run_runner(test_suite)

        value = console.getvalue()
        self.assertTrue('Ran 1 test in ' in value,
                        'Output was:\n%s' % (value,))
        self.assertTrue('OK\n' in value,
                        'Output was:\n%s' % (value,))
