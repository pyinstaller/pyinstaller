#!/usr/bin/env python
#
# Copyright (C) 2011-2012 Martin Zibricky
# Copyright (C) 2011-2012 Hartmut Goebel
# Copyright (C) 2005-2011 Giovanni Bajo
# Based on previous work under copyright (c) 2001, 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

# This program will execute any file with name test*<digit>.py. If your test
# need an aditional dependency name it test*<digit><letter>.py to be ignored
# by this program but be recognizable by any one as a dependency of that
# particular test.


import glob
import optparse
import os
import re
import shutil
import sys


try:
    import PyInstaller
except ImportError:
    # if importing PyInstaller fails, try to load from parent
    # directory to support running without installation.
    import imp
    # Prevent running as superuser (root).
    if not hasattr(os, "getuid") or os.getuid() != 0:
        imp.load_module('PyInstaller', *imp.find_module('PyInstaller',
            [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]))


from PyInstaller import HOMEPATH
from PyInstaller import compat
from PyInstaller.compat import is_py25, is_py26, is_win, is_darwin
from PyInstaller.lib import unittest2 as unittest
from PyInstaller.lib import junitxml
from PyInstaller.utils import misc


VERBOSE = False
REPORT = False
# Directory with this script (runtests.py).
BASEDIR = os.path.dirname(os.path.abspath(__file__))


class MiscDependencies(object):
    """
    Place holder for special requirements of some tests.

    e.g. basic/test_ctypes needs C compiler.

    Every method returns None when successful or a string containing
    error message to be displayed on console.
    """
    def c_compiler(self):
        """
        Check availability of C compiler.
        """
        compiler = None
        msg = 'Cannot find GCC, MinGW or Visual Studio in PATH.'
        if is_win:
            # Try MSVC.
            compiler = misc.find_executable('cl')
        if compiler is None:
            # Try GCC.
            compiler = misc.find_executable('gcc')
            if compiler is None:
                return msg
        return None  # C compiler was found.


class SkipChecker(object):
    """
    Check conditions if a test case should be skipped.
    """
    def __init__(self):
        depend = MiscDependencies()
        # Required Python or OS version for some tests.
        self.MIN_VERSION_OR_OS = {
            'basic/test_celementtree': is_py25,
            'basic/test_email': is_py25,
            # On Mac DYLD_LIBRARY_PATH is not used.
            'basic/test_absolute_ld_library_path': not is_win and not is_darwin,
            'import/test_c_extension': is_py25,
            'import/test_onefile_c_extension': is_py25,
            'import/test_relative_import': is_py25,
            'import/test_relative_import2': is_py26,
            'import/test_relative_import3': is_py25,
            'libraries/test_enchant': is_win,
            # docutils, a sphinx dependency, fails in
            # docutils.utils.__init__.py, function decode_path, where
            # sys.getfilesystemencoding() returns None when frozen.
            # Docutils doesn't expect this and throws an assertion.
            # Untested on Mac, but this shouldn't be a problem, since
            # Macs return 'utf-8'.
            'libraries/test_sphinx': is_win or is_darwin,
            }
        # Required Python modules for some tests.
        self.MODULES = {
            'basic/test_ctypes': ['ctypes'],
            'basic/test_module_attributes': ['xml.etree.cElementTree'],
            'basic/test_nestedlaunch1': ['ctypes'],
            'basic/test_onefile_multiprocess': ['multiprocessing'],
            'libraries/test_enchant': ['enchant'],
            'libraries/test_Image': ['PIL'],
            'libraries/test_Image2': ['PIL'],
            'libraries/test_numpy': ['numpy'],
            'libraries/test_onefile_tkinter': ['Tkinter'],
            'libraries/test_PIL': ['PIL'],
            'libraries/test_PIL2': ['PIL'],
            'libraries/test_pycrypto': ['Crypto'],
            'libraries/test_pyodbc': ['pyodbc'],
            'libraries/test_pyttsx': ['pyttsx'],
            'libraries/test_pytz': ['pytz'],
            'libraries/test_sqlalchemy': ['sqlalchemy', 'MySQLdb', 'psycopg2'],
            'libraries/test_usb': ['ctypes', 'usb'],
            'libraries/test_wx': ['wx'],
            'libraries/test_wx_pubsub': ['wx'],
            'libraries/test_wx_pubsub_arg1': ['wx'],
            'libraries/test_wx_pubsub_kwargs': ['wx'],
            'libraries/test_sphinx': ['sphinx', 'docutils', 'jinja2', 'uuid'],
            'import/test_c_extension': ['simplejson'],
            'import/test_ctypes_cdll_c': ['ctypes'],
            'import/test_ctypes_cdll_c2': ['ctypes'],
            'import/test_eggs2': ['pkg_resources'],
            'import/test_onefile_c_extension': ['simplejson'],
            'import/test_onefile_zipimport': ['pkg_resources'],
            'import/test_onefile_zipimport2': ['pkg_resources', 'setuptools'],
            'interactive/test_pygame': ['pygame'],
            }
        # Other dependecies of some tests.
        self.DEPENDENCIES = {
            'basic/test_ctypes': [depend.c_compiler()],
            # Support for unzipped eggs is not yet implemented.
            # http://www.pyinstaller.org/ticket/541
            'import/test_eggs1': ['Unzipped eggs not yet implemented.'],
            }

    def _check_python_and_os(self, test_name):
        """
        Return True if test name is not in the list or Python or OS
        version is not met.
        """
        if (test_name in self.MIN_VERSION_OR_OS and
                not self.MIN_VERSION_OR_OS[test_name]):
            return False
        return True

    def _check_modules(self, test_name):
        """
        Return name of missing required module, if any. None means
        no module is missing.
        """
        if test_name in self.MODULES:
            for mod_name in self.MODULES[test_name]:
                # STDOUT and STDERR are discarded (devnull) to hide
                # import exceptions.
                trash = open(os.devnull)
                retcode = compat.exec_python_rc('-c', "import %s" % mod_name,
                        stdout=trash, stderr=trash)
                trash.close()
                if retcode != 0:
                    return mod_name
        return None

    def _check_dependencies(self, test_name):
        """
        Return error message when a requirement is not met, None otherwise.
        """
        if test_name in self.DEPENDENCIES:
            for dep in self.DEPENDENCIES[test_name]:
                if dep is not None:
                    return dep
        return None

    def check(self, test_name):
        """
        Check test requirements if they are any specified.

        Return tupple (True/False, 'Reason for skipping.').
        True if all requirements are met. Then test case may
        be executed.
        """
        if not self._check_python_and_os(test_name):
            return (False, 'Required another Python version or OS.')

        required_module = self._check_modules(test_name)
        if required_module is not None:
            return (False, "Module %s is missing." % required_module)

        dependency = self._check_dependencies(test_name)
        if dependency is not None:
            return (False, dependency)

        return (True, 'Requirements met.')


NO_SPEC_FILE = [
    'basic/test_absolute_ld_library_path',
    'basic/test_absolute_python_path',
    'basic/test_email',
    'basic/test_email_oldstyle',
    'basic/test_module__file__attribute',
    'basic/test_onefile_multiprocess',
    'basic/test_onefile_module__file__attribute',
    'basic/test_python_home',
    'import/test_c_extension',
    'import/test_onefile_c_extension',
    'import/test_onefile_zipimport',
    'import/test_onefile_zipimport2',
    'libraries/test_enchant',
    'libraries/test_idlelib',
    'libraries/test_onefile_tkinter',
    'libraries/test_sqlalchemy',
    'libraries/test_pyodbc',
    'libraries/test_pyttsx',
    'libraries/test_sphinx',
    'libraries/test_pytz',
    'libraries/test_usb',
    'libraries/test_wx_pubsub',
    'libraries/test_wx_pubsub_kwargs',
    'libraries/test_wx_pubsub_arg1'
]


class BuildTestRunner(object):

    def __init__(self, test_name, verbose=False, report=False):
        # Use path separator '/' even on windows for test_name name.
        self.test_name = test_name.replace('\\', '/')
        self.verbose = verbose
        self.test_dir, self.test_file = os.path.split(self.test_name)
        # For junit xml report some behavior is changed.
        # Especially redirecting sys.stdout.
        self.report = report

    def _msg(self, text):
        """
        Important text. Print it to console only in verbose mode.
        """
        if self.verbose:
        # This allows to redirect stdout to junit xml report.
            sys.stdout.write('\n' + 10 * '#' + ' ' + text + ' ' + 10 * '#' + '\n\n')
            sys.stdout.flush()

    def _plain_msg(self, text):
        """
        Print text to console only in verbose mode.
        """
        if self.verbose:
            sys.stdout.write(text + '\n')
            sys.stdout.flush()

    def _find_exepath(self, test, parent_dir='dist'):
        of_prog = os.path.join(parent_dir, test)  # one-file deploy filename
        od_prog = os.path.join(parent_dir, test, test)  # one-dir deploy filename

        prog = None
        if os.path.isfile(of_prog):
            prog = of_prog
        elif os.path.isfile(of_prog + ".exe"):
            prog = of_prog + ".exe"
        elif os.path.isdir(of_prog):
            if os.path.isfile(od_prog):
                prog = od_prog
            elif os.path.isfile(od_prog + ".exe"):
                prog = od_prog + ".exe"
        return prog

    def _run_created_exe(self, test, testdir=None):
        """
        Run executable created by PyInstaller.
        """
        self._msg('EXECUTING TEST ' + self.test_name)
        # Run the test in a clean environment to make sure they're
        # really self-contained
        path = compat.getenv('PATH')
        compat.unsetenv('PATH')
        prog = self._find_exepath(test, 'dist')
        if prog is None:
            self._plain_msg('ERROR: no file generated by PyInstaller found!')
            compat.setenv("PATH", path)
            return 1
        else:
            self._plain_msg("RUNNING: " + prog)
            old_wd = os.getcwd()
            os.chdir(os.path.dirname(prog))
            prog = os.path.join(os.curdir, os.path.basename(prog))
            retcode, out, err = compat.exec_command_all(prog)
            os.chdir(old_wd)
            self._msg('STDOUT %s' % self.test_name)
            self._plain_msg(out)
            self._msg('STDERR %s' % self.test_name)
            self._plain_msg(err)
            compat.setenv("PATH", path)
            return retcode

    def test_exists(self):
        """
        Return True if test file exists.
        """
        return os.path.exists(os.path.join(BASEDIR, self.test_name + '.py'))

    def test_building(self):
        """
        Run building of test script.

        Return True if build succeded False otherwise.
        """
        OPTS = ['--debug']

        if self.verbose:
            OPTS.extend(['--debug', '--log-level=INFO'])
        else:
            OPTS.append('--log-level=ERROR')

        # Build executable in onefile mode.
        if self.test_file.startswith('test_onefile'):
            OPTS.append('--onefile')
        else:
            OPTS.append('--onedir')

        self._msg("BUILDING TEST " + self.test_name)

        # Use pyinstaller.py for building test_name.
        testfile_spec = self.test_file + '.spec'
        if not os.path.exists(self.test_file + '.spec'):
            # .spec file does not exist and it has to be generated
            # for main script.
            testfile_spec = self.test_file + '.py'

        pyinst_script = os.path.join(HOMEPATH, 'pyinstaller.py')

        # In report mode is stdout and sys.stderr redirected.
        if self.report:
            # Write output from subprocess to stdout/err.
            retcode, out, err = compat.exec_python_all(pyinst_script,
                  testfile_spec, *OPTS)
            sys.stdout.write(out)
            sys.stdout.write(err)
        else:
            retcode = compat.exec_python_rc(pyinst_script,
                  testfile_spec, *OPTS)

        return retcode == 0

    def test_exe(self):
        """
        Test running of all created executables.
        """
        files = glob.glob(os.path.join('dist', self.test_file + '*'))
        retcode = 0
        for exe in files:
            exe = os.path.splitext(exe)[0]
            retcode_tmp = self._run_created_exe(exe[5:], self.test_dir)
            retcode = retcode or retcode_tmp
        return retcode == 0

    def test_logs(self):
        """
        Compare log files (now used only by multipackage test_name).

        Return True if .toc files match or when .toc patters
        are not defined.
        """
        logsfn = glob.glob(self.test_file + '.toc')
        # Other main scritps do not start with 'test_'.
        logsfn += glob.glob(self.test_file.split('_', 1)[1] + '_?.toc')
        for logfn in logsfn:
            self._msg("EXECUTING MATCHING " + logfn)
            tmpname = os.path.splitext(logfn)[0]
            prog = self._find_exepath(tmpname)
            if prog is None:
                prog = self._find_exepath(tmpname,
                        os.path.join('dist', self.test_file))
            fname_list = compat.exec_python(
                os.path.join(HOMEPATH, 'utils', 'ArchiveViewer.py'),
                '-b', '-r', prog)
            # Fix line-endings so eval() does not fail.
            fname_list = fname_list.replace('\r\n', '\n').replace('\n\r', '\n')
            fname_list = eval(fname_list)
            pattern_list = eval(open(logfn, 'rU').read())
            # Alphabetical order of patterns.
            pattern_list.sort()
            count = 0
            for pattern in pattern_list:
                found = False
                for fname in fname_list:
                    if re.match(pattern, fname):
                        count += 1
                        found = True
                        self._plain_msg('MATCH: %s --> %s' % (pattern, fname))
                        break
                if not found:
                    self._plain_msg('MISSING: %s' % pattern)

            # Not all modules matched.
            # Stop comparing other .toc files and fail the test.
            if count < len(pattern_list):
                return False

        return True


class GenericTestCase(unittest.TestCase):
    def __init__(self, test_dir, func_name):
        """
        test_dir    Directory containing testing python scripts.
        func_name   Name of test function to create.
        """
        self.test_name = test_dir + '/' + func_name

        # Create new test fuction. This has to be done before super().
        setattr(self, func_name, self._generic_test_function)
        super(GenericTestCase, self).__init__(func_name)

        # For tests current working directory has to be changed temporaly.
        self.curr_workdir = os.getcwdu()

    def setUp(self):
        testdir = os.path.dirname(self.test_name)
        os.chdir(os.path.join(BASEDIR, testdir))  # go to testdir
        # For some 'basic' tests we need create file with path to python
        # executable and if it is running in debug mode.
        build_python = open(os.path.join(BASEDIR, 'basic', 'python_exe.build'),
                'w')
        build_python.write(sys.executable + "\n")
        build_python.write('debug=%s' % __debug__ + '\n')
        # On Windows we need to preserve systme PATH for subprocesses in tests.
        build_python.write(os.environ.get('PATH') + '\n')
        build_python.close()

    def tearDown(self):
        os.chdir(self.curr_workdir)  # go back from testdir

    def _generic_test_function(self):
        # Skip test case if test requirement are not met.
        s = SkipChecker()
        req_met, msg = s.check(self.test_name)
        if not req_met:
            raise unittest.SkipTest(msg)
        # Create a build and test it.
        b = BuildTestRunner(self.test_name, verbose=VERBOSE, report=REPORT)
        self.assertTrue(b.test_exists(),
                msg='Test %s not found.' % self.test_name)
        self.assertTrue(b.test_building(),
                msg='Build of %s failed.' % self.test_name)
        self.assertTrue(b.test_exe(),
                msg='Running exe of %s failed.' % self.test_name)
        self.assertTrue(b.test_logs(),
                msg='Matching .toc of %s failed.' % self.test_name)


class BasicTestCase(GenericTestCase):
    test_dir = 'basic'

    def __init__(self, func_name):
        super(BasicTestCase, self).__init__(self.test_dir, func_name)


class ImportTestCase(GenericTestCase):
    test_dir = 'import'

    def __init__(self, func_name):
        super(ImportTestCase, self).__init__(self.test_dir, func_name)


class LibrariesTestCase(GenericTestCase):
    test_dir = 'libraries'

    def __init__(self, func_name):
        super(LibrariesTestCase, self).__init__(self.test_dir, func_name)


class MultipackageTestCase(GenericTestCase):
    test_dir = 'multipackage'

    def __init__(self, func_name):
        super(MultipackageTestCase, self).__init__(self.test_dir, func_name)


class InteractiveTestCase(GenericTestCase):
    """
    Interactive tests require user interaction mostly GUI.

    Interactive tests have to be run directly by user.
    They can't be run by any continuous integration system.
    """
    test_dir = 'interactive'

    def __init__(self, func_name):
        super(InteractiveTestCase, self).__init__(self.test_dir, func_name)


class TestCaseGenerator(object):
    """
    Generate test cases.
    """
    def _detect_tests(self, directory):
        files = glob.glob(os.path.join(directory, 'test_*.py'))
        # Test name is a file name without extension.
        tests = [os.path.splitext(os.path.basename(x))[0] for x in files]
        tests.sort()
        return tests

    def create_suite(self, test_types):
        """
        Create test suite and add test cases to it.

        test_types      Test classes to create test cases from.

        Return test suite with tests.
        """
        suite = unittest.TestSuite()

        for _type in test_types:
            tests = self._detect_tests(_type.test_dir)
            # Create test cases for a specific type.
            for test_name in tests:
                suite.addTest(_type(test_name))

        return suite


def clean():
    """
    Remove temporary files created while running tests.
    """
    # Files/globs to clean up.
    patterns = """python_exe.build
    logdict*.log
    disttest*
    buildtest*
    warn*.txt
    *.py[co]
    */*.py[co]
    */*/*.py[co]
    build/
    dist/
    */*.dll
    */*.lib
    */*.obj
    */*.exp
    */*.so
    */*.dylib
    """.split()

    # By some directories we do not need to clean files.
    # E.g. for unit tests.
    IGNORE_DIRS = set([
        'unit',
    ])

    # Remove temporary files in all subdirectories.
    for directory in os.listdir(BASEDIR):
        if not os.path.isdir(directory):
            continue
        if directory in IGNORE_DIRS:
            continue
        for pattern in patterns:
            file_list = glob.glob(os.path.join(directory, pattern))
            for pth in file_list:
                try:
                    if os.path.isdir(pth):
                        shutil.rmtree(pth)
                    else:
                        os.remove(pth)
                except OSError, e:
                    print e

    # Delete *.spec files for tests without spec file.
    for pth in NO_SPEC_FILE:
        pth = os.path.join(BASEDIR, pth + '.spec')
        if os.path.exists(pth):
            os.remove(pth)


def run_tests(test_suite, xml_file):
    """
    Run test suite and save output to junit xml file if requested.
    """
    if xml_file:
        print 'Writting test results to: %s' % xml_file
        fp = open('report.xml', 'w')
        result = junitxml.JUnitXmlResult(fp)
        # Text from stdout/stderr should be added to failed test cases.
        result.buffer = True
        result.startTestRun()
        test_suite.run(result)
        result.stopTestRun()
        fp.close()
    else:
        unittest.TextTestRunner(verbosity=2).run(test_suite)


def main():
    try:
        parser = optparse.OptionParser(usage='%prog [options] [TEST-NAME ...]',
              epilog='TEST-NAME can be the name of the .py-file, '
              'the .spec-file or only the basename.')
    except TypeError:
        parser = optparse.OptionParser(usage='%prog [options] [TEST-NAME ...]')

    parser.add_option('-c', '--clean', action='store_true',
                      help='Clean up generated files')
    parser.add_option('-i', '--interactive-tests', action='store_true',
                      help='Run interactive tests (default: run normal tests)')
    parser.add_option('-v', '--verbose',
                      action='store_true',
                      default=False,
                      help='Verbose mode (default: %default)')
    parser.add_option('--junitxml', action='store', default=None,
            metavar='FILE', help='Create junit-xml style test report file')

    opts, args = parser.parse_args()

    global VERBOSE, REPORT
    VERBOSE = opts.verbose
    REPORT = opts.junitxml is not None

    # Do only cleanup.
    if opts.clean:
        clean()
        raise SystemExit()  # Exit code is 0 in this case.

    # Run only specified tests.
    if args:
        if opts.interactive_tests:
            parser.error('Must not specify -i/--interactive-tests when passing test names.')
        suite = unittest.TestSuite()
        for arg in args:
            test_list = glob.glob(arg)
            if not test_list:
                test_list = [arg]
            else:
                test_list = [x for x in test_list if os.path.splitext(x)[1] == ".py"]
            for t in test_list:
                test_dir = os.path.dirname(t)
                test_script = os.path.basename(os.path.splitext(t)[0])
                suite.addTest(GenericTestCase(test_dir, test_script))
                print 'Running test:  %s' % (test_dir + '/' + test_script)

    # Run all tests or all interactive tests.
    else:
        if opts.interactive_tests:
            print 'Running interactive tests...'
            test_classes = [InteractiveTestCase]
        else:
            print 'Running normal tests (-i for interactive tests)...'
            test_classes = [BasicTestCase, ImportTestCase,
                    LibrariesTestCase, MultipackageTestCase]

        # Create test suite.
        generator = TestCaseGenerator()
        suite = generator.create_suite(test_classes)

    # Run created test suite.
    clean()
    run_tests(suite, opts.junitxml)


if __name__ == '__main__':
    main()
