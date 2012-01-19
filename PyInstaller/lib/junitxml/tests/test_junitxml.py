#
#  junitxml: extensions to Python unittest to get output junitxml
#  Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
#
#  Copying permitted under the LGPL-3 licence, included with this library.


try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import datetime
import re
import sys
import unittest
import xml.dom.minidom

import junitxml

class TestImports(unittest.TestCase):

    def test_result(self):
        from junitxml import JUnitXmlResult


class TestJUnitXmlResult__init__(unittest.TestCase):

    def test_with_stream(self):
        result = junitxml.JUnitXmlResult(StringIO())


class TestJUnitXmlResult(unittest.TestCase):

    def setUp(self):
        self.output = StringIO()
        self.result = junitxml.JUnitXmlResult(self.output)

    def get_output(self):
        output = self.output.getvalue()
        # Collapse detailed regions into specific strings we can match on
        return re.sub(r'(?s)<failure (.*?)>.*?</failure>',
            r'<failure \1>failure</failure>', re.sub(
            r'(?s)<error (.*?)>.*?</error>', r'<error \1>error</error>',
            re.sub(r'time="\d+\.\d+"', 'time="0.000"', output)))

    def run_test_or_simulate(self, test, method_name, manual_method,
        *manual_args):
        if getattr(test, method_name, None):
            test.run(self.result)
        else:
            # older python - manually execute
            self.result.startTest(test)
            manual_method(test, *manual_args)
            self.result.stopTest(test)

    def test_run_duration_handles_datestamping_in_the_past(self):
        # When used via subunit2junitxml, startTestRun is called before
        # any tz info in the test stream has been seen.
        # So, we use the earliest reported timestamp as the start time,
        # replacing _test_start if needed.
        self.result.startTestRun() # the time is now.
        # Lose an hour (peeks inside, a little naughty but not very).
        self.result.time(self.result._run_start - datetime.timedelta(0, 3600))
        self.result.stopTestRun()
        self.assertEqual("""<testsuite errors="0" failures="0" name="" tests="0" time="0.000">
</testsuite>
""", self.get_output())

    def test_startTestRun_no_output(self):
        # startTestRun doesn't output anything, because JUnit wants an up-front
        # summary.
        self.result.startTestRun()
        self.assertEqual('', self.get_output())

    def test_stopTestRun_outputs(self):
        # When stopTestRun is called, everything is output.
        self.result.startTestRun()
        self.result.stopTestRun()
        self.assertEqual("""<testsuite errors="0" failures="0" name="" tests="0" time="0.000">
</testsuite>
""", self.get_output())

    def test_test_count(self):
        class Passes(unittest.TestCase):
            def test_me(self):
                pass
        self.result.startTestRun()
        Passes("test_me").run(self.result)
        Passes("test_me").run(self.result)
        self.result.stopTestRun()
        # When tests are run, the number of tests is counted.
        output = self.get_output()
        self.assertTrue('tests="2"' in output)

    def test_test_id_with_parameter(self):
        class Passes(unittest.TestCase):
            def id(self):
                return unittest.TestCase.id(self) + '(version_1.6)'
            def test_me(self):
                pass
        self.result.startTestRun()
        Passes("test_me").run(self.result)
        self.result.stopTestRun()
        output = self.get_output()
        self.assertTrue('Passes" name="test_me(version_1.6)"' in output)

    def test_erroring_test(self):
        class Errors(unittest.TestCase):
            def test_me(self):
                1/0
        self.result.startTestRun()
        Errors("test_me").run(self.result)
        self.result.stopTestRun()
        self.assertEqual("""<testsuite errors="1" failures="0" name="" tests="1" time="0.000">
<testcase classname="junitxml.tests.test_junitxml.Errors" name="test_me" time="0.000">
<error type="ZeroDivisionError">error</error>
</testcase>
</testsuite>
""", self.get_output())

    def test_failing_test(self):
        class Fails(unittest.TestCase):
            def test_me(self):
                self.fail()
        self.result.startTestRun()
        Fails("test_me").run(self.result)
        self.result.stopTestRun()
        self.assertEqual("""<testsuite errors="0" failures="1" name="" tests="1" time="0.000">
<testcase classname="junitxml.tests.test_junitxml.Fails" name="test_me" time="0.000">
<failure type="AssertionError">failure</failure>
</testcase>
</testsuite>
""", self.get_output())

    def test_successful_test(self):
        class Passes(unittest.TestCase):
            def test_me(self):
                pass
        self.result.startTestRun()
        Passes("test_me").run(self.result)
        self.result.stopTestRun()
        self.assertEqual("""<testsuite errors="0" failures="0" name="" tests="1" time="0.000">
<testcase classname="junitxml.tests.test_junitxml.Passes" name="test_me" time="0.000"/>
</testsuite>
""", self.get_output())

    def test_skip_test(self):
        class Skips(unittest.TestCase):
            def test_me(self):
                self.skipTest("yo")
        self.result.startTestRun()
        test = Skips("test_me")
        self.run_test_or_simulate(test, 'skipTest', self.result.addSkip, 'yo')
        self.result.stopTestRun()
        output = self.get_output()
        expected = """<testsuite errors="0" failures="0" name="" tests="1" time="0.000">
<testcase classname="junitxml.tests.test_junitxml.Skips" name="test_me" time="0.000">
<skip>yo</skip>
</testcase>
</testsuite>
"""
        self.assertEqual(expected, output)

    def test_unexpected_success_test(self):
        class Succeeds(unittest.TestCase):
            def test_me(self):
                pass
            try:
                test_me = unittest.expectedFailure(test_me)
            except AttributeError:
                pass # Older python - just let the test pass
        self.result.startTestRun()
        Succeeds("test_me").run(self.result)
        self.result.stopTestRun()
        output = self.get_output()
        expected = """<testsuite errors="0" failures="1" name="" tests="1" time="0.000">
<testcase classname="junitxml.tests.test_junitxml.Succeeds" name="test_me" time="0.000">
<failure type="unittest.case._UnexpectedSuccess"/>
</testcase>
</testsuite>
"""
        expected_old = """<testsuite errors="0" failures="0" name="" tests="1" time="0.000">
<testcase classname="junitxml.tests.test_junitxml.Succeeds" name="test_me" time="0.000"/>
</testsuite>
"""
        if output != expected_old:
            self.assertEqual(expected, output)

    def test_expected_failure_test(self):
        expected_failure_support = [True]
        class ExpectedFail(unittest.TestCase):
            def test_me(self):
                self.fail("fail")
            try:
                test_me = unittest.expectedFailure(test_me)
            except AttributeError:
                # Older python - just let the test fail
                expected_failure_support[0] = False
        self.result.startTestRun()
        ExpectedFail("test_me").run(self.result)
        self.result.stopTestRun()
        output = self.get_output()
        expected = """<testsuite errors="0" failures="0" name="" tests="1" time="0.000">
<testcase classname="junitxml.tests.test_junitxml.ExpectedFail" name="test_me" time="0.000"/>
</testsuite>
"""
        expected_old = """<testsuite errors="0" failures="1" name="" tests="1" time="0.000">
<testcase classname="junitxml.tests.test_junitxml.ExpectedFail" name="test_me" time="0.000">
<failure type="AssertionError">failure</failure>
</testcase>
</testsuite>
"""
        if expected_failure_support[0]:
            self.assertEqual(expected, output)
        else:
            self.assertEqual(expected_old, output)


class TestWellFormedXml(unittest.TestCase):
    """XML created should always be well formed even with odd test cases"""

    def _run_and_parse_test(self, case):
        output = StringIO()
        result = junitxml.JUnitXmlResult(output)
        result.startTestRun()
        case.run(result)
        result.stopTestRun()
        return xml.dom.minidom.parseString(output.getvalue())

    def test_failure_with_amp(self):
        """Check the failure element content is escaped"""
        class FailWithAmp(unittest.TestCase):
            def runTest(self):
                self.fail("& should be escaped as &amp;")
        doc = self._run_and_parse_test(FailWithAmp())
        self.assertTrue(
            doc.getElementsByTagName("failure")[0].firstChild.nodeValue
                .endswith("AssertionError: & should be escaped as &amp;\n"))

    def test_quotes_in_test_case_id(self):
        """Check that quotes in an attribute are escaped"""
        class QuoteId(unittest.TestCase):
            def id(self):
                return unittest.TestCase.id(self) + '("quotes")'
            def runTest(self):
                pass
        doc = self._run_and_parse_test(QuoteId())
        self.assertEqual('runTest("quotes")',
            doc.getElementsByTagName("testcase")[0].getAttribute("name"))

    def test_skip_reason(self):
        """Check the skip element content is escaped"""
        class SkipWithLt(unittest.TestCase):
            def runTest(self):
                self.fail("version < 2.7")
            try:
                runTest = unittest.skip("2.7 <= version")(runTest)
            except AttributeError:
                self.has_skip = False
            else:
                self.has_skip = True
        doc = self._run_and_parse_test(SkipWithLt())
        if self.has_skip:
            self.assertEqual('2.7 <= version',
                doc.getElementsByTagName("skip")[0].firstChild.nodeValue)
        else:
            self.assertTrue(
                doc.getElementsByTagName("failure")[0].firstChild.nodeValue
                    .endswith("AssertionError: version < 2.7\n"))

    def test_error_with_control_characters(self):
        """Check C0 control characters are stripped rather than output"""
        class ErrorWithC0(unittest.TestCase):
            def runTest(self):
                raise ValueError("\x1F\x0E\x0C\x0B\x08\x01\x00lost control")
        doc = self._run_and_parse_test(ErrorWithC0())
        self.assertTrue(
            doc.getElementsByTagName("error")[0].firstChild.nodeValue
                .endswith("ValueError: lost control\n"))

    def test_error_with_invalid_cdata(self):
        """Check unicode outside the valid cdata range is stripped"""
        if len("\uffff") == 1:
            # Basic str type supports unicode
            exception = ValueError("\ufffe\uffffEOF")
        else:
            class UTF8_Error(Exception):
                def __unicode__(self):
                    return str(self).decode("UTF-8")
            exception = UTF8_Error("\xef\xbf\xbe\xef\xbf\xbfEOF")
        class ErrorWithBadUnicode(unittest.TestCase):
            def runTest(self):
                raise exception
        doc = self._run_and_parse_test(ErrorWithBadUnicode())
        self.assertTrue(
            doc.getElementsByTagName("error")[0].firstChild.nodeValue
                .endswith("Error: EOF\n"))

    def test_error_with_surrogates(self):
        """Check unicode surrogates are handled properly, paired or otherwise

        This is a pain due to suboptimal unicode support in Python and the
        various changes in Python 3. On UCS-2 builds there is no easy way of
        getting rid of unpaired surrogates while leaving valid pairs alone, so
        this test doesn't require astral characters are kept there.
        """
        if len("\uffff") == 1:
            exception = ValueError("paired: \U000201a2"
                " unpaired: "+chr(0xD800)+"-"+chr(0xDFFF))
            astral_char = "\U000201a2"
        else:
            class UTF8_Error(Exception):
                def __unicode__(self):
                    return str(self).decode("UTF-8")
            exception = UTF8_Error("paired: \xf0\xa0\x86\xa2"
                " unpaired: \xed\xa0\x80-\xed\xbf\xbf")
            astral_char = "\U000201a2".decode("unicode-escape")
        class ErrorWithSurrogates(unittest.TestCase):
            def runTest(self):
                raise exception
        doc = self._run_and_parse_test(ErrorWithSurrogates())
        traceback = doc.getElementsByTagName("error")[0].firstChild.nodeValue
        if sys.maxunicode == 0xFFFF:
            pass # would be nice to handle astral characters properly even so
        else:
            self.assertTrue(astral_char in traceback)
        self.assertTrue(traceback.endswith(" unpaired: -\n"))
