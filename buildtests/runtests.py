#!/usr/bin/env python
# Copyright (C) 2005, Giovanni Bajo
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

# This program will execute any file with name test*<digit>.py. If your test
# need an aditional dependency name it test*<digit><letter>.py to be ignored
# by this program but be recognizable by any one as a dependency of that
# particual test.

import os, sys, glob, string
import pprint
import shutil

HOME = '..'

MIN_VERSION = {
 'test-relative-import': (2,5),
 'test-relative-import2': (2,6),
 'test-relative-import3': (2,5),
 'test-celementtree': (2,5),
 'test9': (2,3),
}

DEPENDENCIES = {
 'test-ctypes-cdll-c': ["ctypes"],
 'test-ctypes-cdll-c2': ["ctypes"],
 'test-numpy': ["numpy"],
 'test-pycrypto': ["Crypto"],
 'test-zipimport1': ["pkg_resources"],
 'test-zipimport2': ["pkg_resources", "setuptools"],
 'test15': ["ctypes"], 
 'test-wx': ["wx"],
}

try:
    here=os.path.dirname(os.path.abspath(__file__))
except NameError:
    here=os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(here)

PYTHON = sys.executable

# On Mac OS X we support only 32bit
# python interpreter can be run as 32bit or 64bit
# run as 32bit
if sys.platform.startswith('darwin'):
    PYTHON = 'arch -i386 ' + PYTHON

if sys.platform[:3] == 'win':
    if string.find(PYTHON, ' ') > -1:
        PYTHON='"%s"' % PYTHON
if __debug__:
    PYOPTS = ""
else:
    PYOPTS = "-O"

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
""".split()

def clean():
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


def _msg(*args, **kw):
    short = kw.get('short', 0)
    sep = kw.get('sep', '#')
    if not short: print
    print sep*20,
    for a in args: print a,
    print sep*20
    if not short: print


def runtests(alltests, filters=None, configfile=None, run_executable=1):
    info = "Executing PyInstaller tests in: %s" % os.getcwd()
    print "*" * min(80, len(info))
    print info
    print "*" * min(80, len(info))

    OPTS = ''
    if configfile:
        # todo: quote correctly
        OTPS = ' -c "%s"' %  configfile

    build_python = open("python_exe.build", "w")
    build_python.write(sys.executable+"\n")
    build_python.write("debug=%s" % __debug__+"\n")
    build_python.close()
    if not filters:
        tests = alltests
    else:
        tests = []
        for part in filters:
            tests += [t for t in alltests if part in t and t not in tests]
    
    tests = [(len(x), x) for x in tests]
    tests.sort()
    path = os.environ["PATH"]
    counter = { "passed": [], "failed": [], "skipped": [] }
    for _,test in tests:
        test = os.path.splitext(os.path.basename(test))[0]
        if test in MIN_VERSION and MIN_VERSION[test] > sys.version_info:
            counter["skipped"].append(test)
            continue
        if test in DEPENDENCIES:
            failed = False
            for mod in DEPENDENCIES[test]:
                res = os.system(PYTHON + ' -c "import %s"' % mod)
                if res != 0:
                    failed = True
                    break
            if failed:
                print "Skipping test because module %s is missing" % mod
                counter["skipped"].append(test)
                continue
        _msg("BUILDING TEST", test)
        prog = string.join([PYTHON, PYOPTS, os.path.join(HOME, 'Build.py'),
                            OPTS, test+".spec"],
                           ' ')
        print "BUILDING:", prog
        res = os.system(prog)
        if res == 0 and run_executable:
            _msg("EXECUTING TEST", test)
            # Run the test in a clean environment to make sure they're
            # really self-contained
            del os.environ["PATH"]

            of_prog = os.path.join('dist', test) # one-file deploy filename
            od_prog = os.path.join('dist', test, test) # one-dir deploy filename

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

            if prog is None:
                res = 1
                print "ERROR: no file generated by PyInstaller found!"
            else:
                print "RUNNING:", prog
                res = os.system(prog)
            os.environ["PATH"] = path

        if res == 0:
            _msg("FINISHING TEST", test, short=1)
            counter["passed"].append(test)
        else:
            _msg("TEST", test, "FAILED", short=1, sep="!!")
            counter["failed"].append(test)
    pprint.pprint(counter)


if __name__ == '__main__':
    normal_tests = glob.glob('test*.spec')
    interactive_tests = glob.glob('test*i.spec')

    try:
        from optparse import OptionParser
    except ImportError:
        sys.path.append("..")
        from pyi_optparse import OptionParser
        
    if sys.version_info < (2,5):
        parser = OptionParser(usage="%prog [options] [TEST-NAME ...]")
    else:
        parser = OptionParser(usage="%prog [options] [TEST-NAME ...]",
                              epilog="TEST-NAME can be the name of the .py-file, the .spec-file or only the basename.")
    
    parser.add_option('-c', '--clean', action='store_true',
                      help='Clean up generated files')
    parser.add_option('-i', '--interactive-tests', action='store_true',
                      help='Run interactive tests (default: run normal tests)')
    parser.add_option('-n', '--no-run', action='store_true',
                      help='Do not run the built executables. '
                           'Useful for cross builds.')
    parser.add_option('-C', '--configfile',
                      default=os.path.join(HOME, 'config.dat'),
                      help='Name of generated configfile (default: %default)')

    opts, args = parser.parse_args()

    if opts.clean:
        clean()
        raise SystemExit()

    if args:
        if opts.interactive_tests:
            parser.error('Must not specify -i/--interactive-tests when passing test names.')
        tests = args
    elif opts.interactive_tests:
        print "Running interactive tests"
        tests = interactive_tests
    else:
        tests = [t for t in normal_tests if t not in interactive_tests]
        print "Running normal tests (-i for interactive tests)"

    clean()
    runtests(tests, configfile=opts.configfile, run_executable=not opts.no_run)
