#
#  junitxml: extensions to Python unittest to get output junitxml
#  Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
#
#  Copying permitted under the LGPL-3 licence, included with this library.

"""unittest compatible JUnit XML output."""


import datetime
import re
import time
import unittest2 as unittest

# same format as sys.version_info: "A tuple containing the five components of
# the version number: major, minor, micro, releaselevel, and serial. All
# values except releaselevel are integers; the release level is 'alpha',
# 'beta', 'candidate', or 'final'. The version_info value corresponding to the
# Python version 2.0 is (2, 0, 0, 'final', 0)."  Additionally we use a
# releaselevel of 'dev' for unreleased under-development code.
#
# If the releaselevel is 'alpha' then the major/minor/micro components are not
# established at this point, and setup.py will use a version of next-$(revno).
# If the releaselevel is 'final', then the tarball will be major.minor.micro.
# Otherwise it is major.minor.micro~$(revno).
__version__ = (0, 6, 0, 'final', 0)


def test_suite():
    import junitxml.tests
    return junitxml.tests.test_suite()


class LocalTimezone(datetime.tzinfo):

    def __init__(self):
        self._offset = None

    # It seems that the minimal possible implementation is to just return all
    # None for every function, but then it breaks...
    def utcoffset(self, dt):
        if self._offset is None:
            t = 1260423030 # arbitrary, but doesn't handle dst very well
            dt = datetime.datetime
            self._offset = (dt.fromtimestamp(t) - dt.utcfromtimestamp(t))
        return self._offset

    def dst(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return None


def _error_name(eclass):
    module = eclass.__module__
    if module not in ("__main__", "builtins", "exceptions"):
        return ".".join([module, eclass.__name__])
    return eclass.__name__


_non_cdata = "[\0-\b\x0B-\x1F\uD800-\uDFFF\uFFFE\uFFFF]+"
if "\\u" in _non_cdata:
    _non_cdata = _non_cdata.decode("unicode-escape")
    def _strip_invalid_chars(s, _sub=re.compile(_non_cdata, re.UNICODE).sub):
        if not isinstance(s, unicode):
            try:
                s = s.decode("utf-8")
            except UnicodeDecodeError:
                s = s.decode("ascii", "replace")
        return _sub("", s).encode("utf-8")
else:
    def _strip_invalid_chars(s, _sub=re.compile(_non_cdata, re.UNICODE).sub):
        return _sub("", s)
def _escape_content(s):
    return (_strip_invalid_chars(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace("]]>", "]]&gt;"))
def _escape_attr(s):
    return (_strip_invalid_chars(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace("]]>", "]]&gt;")
        .replace('"', "&quot;")
        .replace("\t", "&#x9;")
        .replace("\n", "&#xA;"))


class JUnitXmlResult(unittest.TestResult):
    """A TestResult which outputs JUnit compatible XML."""
    
    def __init__(self, stream):
        """Create a JUnitXmlResult.

        :param stream: A stream to write results to. Note that due to the
            nature of JUnit XML output, nnothing will be written to the stream
            until stopTestRun() is called.
        """
        self.__super = super(JUnitXmlResult, self)
        self.__super.__init__()
        # GZ 2010-09-03: We have a problem if passed a text stream in Python 3
        #                as really we want to write raw UTF-8 to ensure that
        #                the encoding is not mangled later
        self._stream = stream
        self._results = []
        self._set_time = None
        self._test_start = None
        self._run_start = None
        self._tz_info = None

    def startTestRun(self):
        """Start a test run."""
        self._run_start = self._now()

    def _get_tzinfo(self):
        if self._tz_info is None:
            self._tz_info = LocalTimezone()
        return self._tz_info

    def _now(self):
        if self._set_time is not None:
            return self._set_time
        else:
            return datetime.datetime.now(self._get_tzinfo())

    def time(self, a_datetime):
        self._set_time = a_datetime
        if (self._run_start is not None and
            self._run_start > a_datetime):
            self._run_start = a_datetime

    def startTest(self, test):
        self.__super.startTest(test)
        self._test_start = self._now()

    def _duration(self, from_datetime):
        try:
            delta = self._now() - from_datetime
        except TypeError:
            n = self._now()
            delta = datetime.timedelta(-1)
        seconds = delta.days * 3600*24 + delta.seconds
        return seconds + 0.000001 * delta.microseconds

    def _test_case_string(self, test):
        duration = self._duration(self._test_start)
        test_id = test.id()
        # Split on the last dot not inside a parameter
        class_end = test_id.rfind(".", 0, test_id.find("("))
        if class_end == -1:
            classname, name = "", test_id
        else:
            classname, name = test_id[:class_end], test_id[class_end+1:]
        self._results.append('<testcase classname="%s" name="%s" '
            'time="%0.3f"' % (_escape_attr(classname), _escape_attr(name), duration))

    def stopTestRun(self):
        """Stop a test run.

        This allows JUnitXmlResult to output the XML representation of the test
        run.
        """
        duration = self._duration(self._run_start)
        self._stream.write('<testsuite errors="%d" failures="%d" name="" '
            'skips="%d" tests="%d" time="%0.3f">\n' % (len(self.errors),
            len(self.failures) + len(getattr(self, "unexpectedSuccesses", ())),
            len(self.skipped), self.testsRun, duration))
        self._stream.write(''.join(self._results))
        self._stream.write('</testsuite>\n')

    def addError(self, test, error):
        self.__super.addError(test, error)
        self._test_case_string(test)
        self._results.append('>\n')
        self._results.append('<error type="%s">%s</error>\n</testcase>\n' % (
            _escape_attr(_error_name(error[0])),
            _escape_content(self._exc_info_to_string(error, test))))

    def addFailure(self, test, error):
        self.__super.addFailure(test, error)
        self._test_case_string(test)
        self._results.append('>\n')
        self._results.append('<failure type="%s">%s</failure>\n</testcase>\n' %
            (_escape_attr(_error_name(error[0])),
            _escape_content(self._exc_info_to_string(error, test))))

    def addSuccess(self, test):
        self.__super.addSuccess(test)
        self._test_case_string(test)
        self._results.append('/>\n')

    def addSkip(self, test, reason):
        try:
            self.__super.addSkip(test, reason)
        except AttributeError:
            # Python < 2.7|3.1
            pass
        self._test_case_string(test)
        self._results.append('>\n')
        self._results.append('<skipped message="%s"></skipped>\n</testcase>\n'% _escape_attr(reason))

    def addUnexpectedSuccess(self, test):
        try:
            self.__super.addUnexpectedSuccess(test)
        except AttributeError:
            # Python < 2.7|3.1
            pass
        self._test_case_string(test)
        self._results.append('>\n')
        self._results.append('<failure type="unittest.case._UnexpectedSuccess"/>\n</testcase>\n')

    def addExpectedFailure(self, test, error):
        try:
            self.__super.addExpectedFailure(test, error)
        except AttributeError:
            # Python < 2.7|3.1
            pass
        self._test_case_string(test)
        self._results.append('/>\n')

