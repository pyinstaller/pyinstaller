"""Simple Test Runner for XML output.

Writes XML output and reports test status to stderr.

:Author: Duncan Findlay <duncan@duncf.ca>
"""
import sys
import time

import junitxml

class JUnitXmlTestRunner(object):

    """Simple Test Runner that writes XML output and reports status.

    Provides high-level status suitable for command-line operation as well as
    XML output.
    """

    resultclass = junitxml.JUnitXmlResult

    def __init__(self, xml_stream, txt_stream=None, **kwargs):
        if txt_stream is None:
            txt_stream = sys.stderr
        self._txt_stream = txt_stream
        self._xml_stream = xml_stream

    def _make_result(self):
        return self.resultclass(self._xml_stream)

    def run(self, test):
        result = self._make_result()
        result.startTestRun()

        start_time = time.time()
        test.run(result)
        end_time = time.time()

        result.stopTestRun()

        self._write_summary(result, end_time - start_time)
        return result

    def _write_summary(self, result, time_elapsed):

        plural = ''
        if result.testsRun != 1:
            plural = 's'

        self._txt_stream.write('Ran %d test%s in %.3fs\n\n' %
                               (result.testsRun, plural, time_elapsed))
        test_info = []

        for result_attr, desc in (
            ('failures', 'failures'), ('errors', 'errors'),
            ('skipped', 'skipped'), ('expectedFailures', 'expected failures'),
            ('unexpectedSuccesses', 'unexpected successes')):

            num = len(getattr(result, result_attr, []))
            if num > 0:
                test_info.append('%s=%s' % (desc, num))

        test_info_str = ''
        if test_info:
            test_info_str = ' (%s)' % (', '.join(test_info),)

        if result.wasSuccessful():
            self._txt_stream.write('OK%s\n' % (test_info_str,))
        else:
            self._txt_stream.write('FAILED%s\n' % (test_info_str,))

