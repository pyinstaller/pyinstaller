"""Command line functionality for junitxml.

Runs specific tests or does automatic discovery with output in XML format.

:Author: Duncan Findlay <duncan@duncf.ca>
"""
import optparse
import sys

# If we're using Python < 2.7, we want unittest2 if we can get it, otherwise
# unittest will suffice.
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import junitxml
import junitxml.runner

ADDITIONAL_HELP_NO_DISCOVERY = """\

<xml file> is the name of a file used for output.
<tests> is a list of any number of test modules, classes and test
methods. If no tests are specified, automatic discovery is performed.

Example for executing specific tests:
  %(prog_name)s -o junit.xml test_module
  %(prog_name)s test_module.TestClass
  %(prog_name)s test_module.TestClass.test_method
"""

ADDITIONAL_HELP_DISCOVERY = """\

<xml file> is the name of a file used for output.
[tests] can be a list of any number of test modules, classes and test
methods. If no tests are specified, automatic discovery is performed.

Example for executing specific tests:
  %(prog_name)s -o junit.xml test_module
  %(prog_name)s test_module.TestClass
  %(prog_name)s test_module.TestClass.test_method

Example for test discovery:
  %(prog_name)s
  %(prog_name)s -o junit.xml -s tests/ -p '*.py'
  %(prog_name)s -t myproj/ -s myproj/tests/ -p '*.py'

For test discovery all test modules must be importable from the top
level directory of the project.

It is an error to specify discovery options and specific tests.
"""

class XmlTestProgram(object):
    """Command line program for running tests with XML output."""

    loader = unittest.defaultTestLoader
    runner_class = junitxml.runner.JUnitXmlTestRunner

    def __init__(self, can_discover=None):
        self.tests = None
        self.output_filename = None

        self._can_discover = can_discover
        if self._can_discover is None:
            self._can_discover = bool(hasattr(self.loader, 'discover'))

        if self._can_discover:
            self._usage = 'Usage: %prog [options] [tests]'
            self._help = ADDITIONAL_HELP_DISCOVERY
        else:
            self._usage = 'Usage: %prog [options] <tests>'
            self._help = ADDITIONAL_HELP_NO_DISCOVERY

    def parse_args(self, argv=None):
        """Parse command line arguments."""
        parser = optparse.OptionParser(
            usage=self._usage, add_help_option=False)

        parser.add_option('-h', '--help', dest='help', action='store_true',
                          help='Show option summary and exit')
        parser.add_option(
            '-o', '--output-file', dest='output',
            help='Specify name of output XML file. (Default: %default)',
            default='./junit.xml')

        if self._can_discover:
            discovery_group = optparse.OptionGroup(
                parser, 'Discovery options',
                'Used to control discovery (when no tests specified).')

            discovery_group.add_option(
                '-s', '--start-directory', dest='start',
                default=None, help="Directory to start discovery "
                "('.' default)")
            discovery_group.add_option(
                '-p', '--pattern', dest='pattern',  default=None,
                help="Pattern to match tests ('test*.py' default)")
            discovery_group.add_option(
                '-t', '--top-level-directory', dest='top', default=None,
                help='Top level directory of project (defaults to start '
                'directory)')
            parser.add_option_group(discovery_group)

        if argv is None:
            argv = sys.argv[1:]
        options, args = parser.parse_args(argv)

        if options.help:
            parser.print_help()
            sys.stdout.write(self._help % ({'prog_name': sys.argv[0]}))
            sys.exit(1)

        self.output_filename = options.output

        if self._can_discover and args and \
               (options.start or options.pattern or options.top):
            parser.error(
                'Cannot specify discovery options and specific tests.')
        elif args:
            self.tests = self._load_tests(args)
        elif self._can_discover:
            self.tests = self._do_discovery(options.start, options.pattern,
                                            options.top)
        else:
            parser.error('Must specify tests to run.')

    def _do_discovery(self, start_dir, pattern, top_level_dir):
        assert self._can_discover

        if start_dir is None:
            start_dir = '.'
        if pattern is None:
            pattern = 'test*.py'
        if top_level_dir is None:
            top_level_dir = start_dir

        return self.loader.discover(start_dir, pattern, top_level_dir)

    def _load_tests(self, test_names):
        return self.loader.loadTestsFromNames(test_names)

    def run(self):
        """Run the specified tests.

        :Returns: TestResult object.
        """
        stream = open(self.output_filename, 'w')
        try:
            test_runner = self.runner_class(xml_stream=stream)
            return test_runner.run(self.tests)
        finally:
            stream.close()


def main(args=None, prog=None):
    if args is None:
        args = sys.argv[1:]
    if prog is None:
        prog = XmlTestProgram()

    prog.parse_args(args)
    result = prog.run()
    sys.exit(int(not result.wasSuccessful()))

if __name__ == '__main__':
    main()
