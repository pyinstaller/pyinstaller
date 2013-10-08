"""Test "main" functionality for junitxml.

:Author: Duncan Findlay <duncan@duncf.ca>
"""
import os
import shutil
import sys
import tempfile
import xml.dom.minidom
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import junitxml.main

def _skip_if(condition):
    """Decorator for skipping tests no matter what version of unittest."""
    if condition:
        def decorator(func):
            if hasattr(unittest, 'skip'):
                # If we don't have discovery, we probably don't skip, but we'll
                # try anyways...
                return unittest.skip('Discovery not supported.')(func)
            else:
                return None
        return decorator
    else:
        # Condition is false, return the do-nothing decorator.
        def decorator(func):
            return func
        return decorator


class FakeLoader(object):
    """Fake TestLoader to stub out test loading."""

    def discover(self, start_dir, pattern=None, top_level_dir=None):
        self._did_discovery = (start_dir, pattern, top_level_dir)
        return unittest.TestSuite()

    def loadTestsFromNames(self, names, module=None):
        self._loaded_tests = (names, module)
        return unittest.TestSuite()


class RedirectedTestCase(unittest.TestCase):

    """Redirects test output away from stdout/stderr."""

    def setUp(self):
        self._stderr = StringIO()
        self._stdout = StringIO()
        self._old_stderr = sys.stderr
        self._old_stdout = sys.stdout
        sys.stderr = self._stderr
        sys.stdout = self._stdout

    def tearDown(self):
        sys.stderr = self._old_stderr
        sys.stdout = self._old_stdout


class TestArgs(RedirectedTestCase):

    def _test_bad_args(self, args, can_discover=None):
        # XmlTestPrograrm uses some magic to figure out whether it can do test
        # discovery. We want to manually control that, sometimes.
        try:
            if can_discover is not None:
                prog = junitxml.main.XmlTestProgram(can_discover=can_discover)
                junitxml.main.main(args, prog=prog)
            else:
                junitxml.main.main(args)
            self.fail('No exception thrown')
        except SystemExit:
            e = sys.exc_info()[1]
            self.assertEqual(e.code, 2, self._stderr.getvalue())
        except:
            self.fail('No SystemExit exception thrown')

    def test_bad_opts(self):
        """Bad option combinations are rejected."""
        # Mix of tests and discovery opts.
        self._test_bad_args(['-s', '..', 'my_test'])
        self._test_bad_args(['-p', 'foo*.py', 'my_test'])
        self._test_bad_args(['-t', '..', 'my_test'])
        self._test_bad_args(['--top', '..', 'my_test'])

        # Incomplete options.
        self._test_bad_args(['-o'])
        self._test_bad_args(['-p'])
        self._test_bad_args(['-s'])
        self._test_bad_args(['-t'])

    def test_help(self):
        """Help is displayed with --help."""
        try:
            junitxml.main.main(['--help'])
        except SystemExit:
            e = sys.exc_info()[1]
            self.assertEqual(e.code, 1)
        except:
            self.fail('No SystemExit exception thrown.')
        self.assertTrue('Example ' in self._stdout.getvalue())

    def test_no_discovery(self):
        """Discovery options are rejected if discovery is not available."""
        self._test_bad_args([], can_discover=False)
        self._test_bad_args(['-s', '..'], can_discover=False)
        self._test_bad_args(['-t', '..'], can_discover=False)
        self._test_bad_args(['-p', '*.*'], can_discover=False)


class TestLoad(RedirectedTestCase):

    def setUp(self):
        super(TestLoad, self).setUp()
        self._tmpdir = tempfile.mkdtemp(prefix='unittest_junitxml_')
        self._output_file = os.path.join(self._tmpdir, 'junit.xml')

    def tearDown(self):
        super(TestLoad, self).tearDown()
        shutil.rmtree(self._tmpdir)

    def test_loaded_tests(self):
        """Verify named tests are properly loaded."""
        prog = junitxml.main.XmlTestProgram()
        prog.loader = FakeLoader()
        prog.parse_args(['-o', self._output_file, 'my_test1', 'my_test2'])
        result = prog.run()

        document = xml.dom.minidom.parse(self._output_file)
        self.assertEqual(document.documentElement.tagName, 'testsuite')
        self.assertEqual(document.documentElement.getAttribute('tests'), '0')

        self.assertEqual(result.wasSuccessful(), True)
        self.assertTrue(hasattr(prog.loader, '_loaded_tests'))
        self.assertEqual(prog.loader._loaded_tests,
                         (['my_test1', 'my_test2'], None))

    def test_discovery_all_args(self):
        """Verify cmdline opts are used for discovery."""
        prog = junitxml.main.XmlTestProgram(can_discover=True)
        prog.loader = FakeLoader()
        prog.parse_args(['-o', self._output_file, '-s', self._tmpdir,
                         '--pattern', '*.py', '-t', '.'])
        result = prog.run()

        document = xml.dom.minidom.parse(self._output_file)
        self.assertEqual(document.documentElement.tagName, 'testsuite')
        self.assertEqual(document.documentElement.getAttribute('tests'), '0')

        self.assertEqual(result.wasSuccessful(), True)
        self.assertTrue(hasattr(prog.loader, '_did_discovery'))
        self.assertEqual(prog.loader._did_discovery,
                         (self._tmpdir, '*.py', '.'))

    def test_discovery_top_dir(self):
        """Verify top-level dir properly defaults to start directory."""
        prog = junitxml.main.XmlTestProgram(can_discover=True)
        prog.loader = FakeLoader()
        prog.parse_args(['-o', self._output_file, '--start-dir', self._tmpdir])
        result = prog.run()

        document = xml.dom.minidom.parse(self._output_file)
        self.assertEqual(document.documentElement.tagName, 'testsuite')
        self.assertEqual(document.documentElement.getAttribute('tests'), '0')

        self.assertEqual(result.wasSuccessful(), True)
        self.assertTrue(hasattr(prog.loader, '_did_discovery'))
        self.assertEqual(prog.loader._did_discovery,
                         (self._tmpdir, 'test*.py', self._tmpdir))

    def test_discovery_no_args(self):
        """Verify good defaults are used for discovery when not specified."""
        prog = junitxml.main.XmlTestProgram(can_discover=True)
        prog.loader = FakeLoader()
        prog.parse_args(['-o', self._output_file])
        result = prog.run()

        document = xml.dom.minidom.parse(self._output_file)
        self.assertEqual(document.documentElement.tagName, 'testsuite')
        self.assertEqual(document.documentElement.getAttribute('tests'), '0')

        self.assertEqual(result.wasSuccessful(), True)
        self.assertTrue(hasattr(prog.loader, '_did_discovery'))
        self.assertEqual(prog.loader._did_discovery,
                         ('.', 'test*.py', '.'))
