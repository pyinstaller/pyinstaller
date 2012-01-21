#!/usr/bin/env python
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
# particual test.

import os
import sys
import glob
import re
import pprint
import shutil
import optparse
import functools

try:
    import PyInstaller
except ImportError:
    # if importing PyInstaller fails, try to load from parent
    # directory to support running without installation
    import imp
    if not hasattr(os, "getuid") or os.getuid() != 0:
        imp.load_module('PyInstaller', *imp.find_module('PyInstaller',
            [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]))


from PyInstaller import HOMEPATH
from PyInstaller import is_py23, is_py25, is_py26, is_win, is_darwin
from PyInstaller import compat
from PyInstaller.lib import unittest2 as unittest


class SkipChecker(object):
    """
    Check conditions if a test case should be skipped.
    """
    MIN_VERSION_OR_OS = {
        'basic/test_time': is_py23,
        'basic/test_celementtree': is_py25,
        'basic/test_email2': is_py23,
        # On Mac DYLD_LIBRARY_PATH is not used.
        'basic/test_absolute_ld_library_path': not is_win and not is_darwin,
        'import/test_relative_import': is_py25,
        'import/test_relative_import2': is_py26,
        'import/test_relative_import3': is_py25,
        'libraries/test_enchant': is_win,
    }

    DEPENDENCIES = {
        'basic/test_ctypes': ['ctypes'],
        'basic/test_nestedlaunch1': ['ctypes'],
        'libraries/test_enchant': ['enchant'],
        'libraries/test_Image': ['Image'],
        'libraries/test_numpy': ['numpy'],
        'libraries/test_PIL': ['PIL'],
        'libraries/test_PIL2': ['PIL'],
        'libraries/test_pycrypto': ['Crypto'],
        'libraries/test_sqlalchemy': ['sqlalchemy', 'MySQLdb', 'psycopg2'],
        'libraries/test_wx': ['wx'],
        'import/test_ctypes_cdll_c': ['ctypes'],
        'import/test_ctypes_cdll_c2': ['ctypes'],
        'import/test_zipimport1': ['pkg_resources'],
        'import/test_zipimport2': ['pkg_resources', 'setuptools'],
        'interactive/test_pygame': ['pygame'],
    }

    def _check_python_and_os(self, test_name):
        """
        Return True if test name is not in the list or Python or OS
        version is not met.
        """
        if (test_name in SkipChecker.MIN_VERSION_OR_OS and
                not SkipChecker.MIN_VERSION_OR_OS[test_name]):
            return False
        return True

    def _check_dependencies(self, test_name):
        """
        Return name of missing required module, if any. None means
        no module is missing.
        """
        if test_name in SkipChecker.DEPENDENCIES:
            for mod_name in SkipChecker.DEPENDENCIES[test_name]:
                retcode = compat.exec_python_rc('-c', "import %s" % mod_name)
                if retcode != 0:
                    return mod_name
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

        required_module = self._check_dependencies(test_name)

        if required_module is not None:
            return (False, "Module %s is missing." % required_module)
        else:
            return (True, 'Requirements met.')


NO_SPEC_FILE = [
    'basic/test_absolute_ld_library_path',
    'basic/test_absolute_python_path',
    'libraries/test_enchant',
    'libraries/test_sqlalchemy',
]


TEST_DIRS = ['basic', 'import', 'libraries', 'multipackage']
INTERACT_TEST_DIRS = ['interactive']


# files/globs to clean up
CLEANUP = """python_exe.build
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
*/*.so
*/*.dylib
""".split()


def clean():
    for d in TEST_DIRS + INTERACT_TEST_DIRS:
        os.chdir(d)
        for clean in CLEANUP:
            clean = glob.glob(clean)
            for path in clean:
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except OSError, e:
                    print e
        os.chdir('..')
    # delete *.spec files for tests without spec
    for path in NO_SPEC_FILE:
        path += '.spec'
        if os.path.exists(path):
            os.remove(path)


def _msg(*args, **kw):
    short = kw.get('short', 0)
    sep = kw.get('sep', '#')
    if not short:
        print
    print sep * 20,
    for a in args:
        print a,
    print sep * 20
    if not short:
        print


def run_configure(verbose=False):
    """
    Run configure phase. The same configuration can be used
    for all tests and tests take then less time.
    """
    log_level = 'DEBUG' if verbose else 'WARN'
    # run configure phase.
    compat.exec_python_rc(os.path.join(HOMEPATH, 'utils', 'Configure.py'),
            '--log-level=%s' % log_level)


def runtests(test_name, verbose=False):
    # Use path separator '/' even on windows for test names.
    if is_win:
        test_name = [x.replace('\\', '/') for x in test_name]

    info = "Executing PyInstaller test_name in: %s" % os.getcwd()
    print "*" * min(80, len(info))
    print info
    print "*" * min(80, len(info))

    OPTS = ['--skip-configure', '--debug']

    build_python = open('basic/python_exe.build', 'w')
    build_python.write(sys.executable + "\n")
    build_python.write('debug=%s' % __debug__ + '\n')
    build_python.close()

    test_name = [(len(x), x) for x in test_name]
    test_name.sort()
    counter = {"passed": [], "failed": [], "skipped": []}

    # execute test
    testbasedir = os.getcwdu()

    test = os.path.splitext(test_name[0][1])[0]
    if not os.path.exists(test + '.py'):
        _msg("Testfile not found:", test + '.py', short=1)
        counter["failed"].append(test)
        return False
    testdir, testfile = os.path.split(test)
    if not testdir:
        testdir = '.'
    elif not os.path.exists(testdir):
        os.makedirs(testdir)
    os.chdir(testdir)  # go to testdir
    _msg("BUILDING TEST", test)

    # use pyinstaller.py for building test_name
    testfile_spec = testfile + '.spec'
    if not os.path.exists(testfile + '.spec'):
        # .spec file does not exist and it has to be generated
        # for main script
        testfile_spec = testfile + '.py'

    res = compat.exec_python_rc(os.path.join(HOMEPATH, 'pyinstaller.py'),
                      testfile_spec, *OPTS)
    if res == 0:
        files = glob.glob(os.path.join('dist', testfile + '*'))
        for exe in files:
            exe = os.path.splitext(exe)[0]
            res_tmp = test_exe(exe[5:], testdir)
            res = res or res_tmp

    # compare log files (now used only by multipackage test_name)
    logsfn = glob.glob(testfile + '.toc')
    # other main scritps do not start with 'test_'
    logsfn += glob.glob(testfile.split('_', 1)[1] + '_?.toc')
    for logfn in logsfn:
        _msg("EXECUTING MATCHING", logfn)
        tmpname = os.path.splitext(logfn)[0]
        prog = find_exepath(tmpname)
        if prog is None:
            prog = find_exepath(tmpname, os.path.join('dist', testfile))
        fname_list = compat.exec_python(
            os.path.join(HOMEPATH, 'utils', 'ArchiveViewer.py'),
            '-b', '-r', prog)
        fname_list = eval(fname_list)
        pattern_list = eval(open(logfn, 'rU').read())
        count = 0
        for pattern in pattern_list:
            found = False
            for fname in fname_list:
                if re.match(pattern, fname):
                    count += 1
                    found = True
                    if verbose:
                        print "MATCH: %s --> %s" % (pattern, fname)
                    break
            if not found:
                if verbose:
                    print "MISSING: %s" % pattern
        if count < len(pattern_list):
            res = 1
            print "Matching FAILED!"
        else:
            print "Matching SUCCESS!"

    if res == 0:
        _msg("FINISHING TEST", test, short=1)
        counter["passed"].append(test)
    else:
        _msg("TEST", test, "FAILED", short=1, sep="!!")
        counter["failed"].append(test)
    os.chdir(testbasedir)  # go back from testdir
    pprint.pprint(counter)


def test_exe(test, testdir=None):
    _msg("EXECUTING TEST", testdir + '/' + test)
    # Run the test in a clean environment to make sure they're
    # really self-contained
    path = compat.getenv("PATH")
    compat.unsetenv("PATH")
    prog = find_exepath(test, 'dist')
    if prog is None:
        print "ERROR: no file generated by PyInstaller found!"
        compat.setenv("PATH", path)
        return 1
    else:
        print "RUNNING:", prog
        tmp = compat.exec_command_rc(prog)
        compat.setenv("PATH", path)
        return tmp


def find_exepath(test, parent_dir='dist'):
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


def detect_tests(folders):
    tests = []
    for f in folders:
        tests += glob.glob(os.path.join(f, 'test_*.py'))
    return tests


def main():
    # Change working directory to place where this script is.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    try:
        parser = optparse.OptionParser(usage='%prog [options] [TEST-NAME ...]',
              epilog='TEST-NAME can be the name of the .py-file, the .spec-file or only the basename.')
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

    opts, args = parser.parse_args()

    if opts.clean:
        clean()
        raise SystemExit()

    if args:
        if opts.interactive_tests:
            parser.error('Must not specify -i/--interactive-tests when passing test names.')
        # run all tests in specified dir
        if args[0] in TEST_DIRS:
            tests = detect_tests(args)
        # run only single specified tests
        else:
            tests = args
    elif opts.interactive_tests:
        print "Running interactive tests"
        tests = detect_tests(INTERACT_TEST_DIRS)
    else:
        print "Running normal tests (-i for interactive tests)"
        tests = detect_tests(TEST_DIRS)

    clean()
    runtests(tests, verbose=opts.verbose)


class GenericTestCase(unittest.TestCase):
    
    def setUp(self):
        # Remove temporary files from previous runs.
        clean()


class BasicTestCase(GenericTestCase):
    pass


def generic_test_function(test_name):
    # Skip test case if test requirement are not met.
    s = SkipChecker()
    req_met, msg = s.check(test_name)
    if not req_met:
        raise unittest.SkipTest(msg)
    # Create a build and run it.
    runtests([test_name + '.py'], verbose=True)


if __name__ == '__main__':
    #main()
    run_configure()
    for case in ['test_1']:
        testname = case
        testfunc = functools.partial(generic_test_function,
            os.path.join('basic', case))
        testfunc.__doc__ = testname
        setattr(BasicTestCase, testname, testfunc)
    unittest.main(verbosity=2)
