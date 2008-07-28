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
import shutil

try:
    here=os.path.dirname(os.path.abspath(__file__))
except NameError:
    here=os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(here)
PYTHON = sys.executable
if sys.platform[:3] == 'win':
    if string.find(PYTHON, ' ') > -1:
        PYTHON='"%s"' % PYTHON

# files/globs to clean up
CLEANUP = """python_exe.build
logdict*.log
disttest*
buildtest*
warn*.txt
*.py[co]
*/*.py[co]
*/*/*.py[co]
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
    if not short: print
    print "##################",
    for a in args: print a,
    print "#######################"
    if not short: print


def runtests(alltests, filters=None, run_executable=1):
    info = "Executing PyInstaller tests in: %s" % os.getcwd()
    print "*"*len(info)
    print info
    print "*"*len(info)

    build_python = open("python_exe.build", "w")
    build_python.write(sys.executable)
    build_python.close()
    if not filters:
        tests = alltests
    else:
        tests = []
        for part in filters:
            tests += [t for t in alltests if part in t and t not in tests]
    tests.sort(key=lambda x: (len(x), x)) # test1 < test10
    path = os.environ["PATH"]
    counter = dict(passed=[],failed=[])
    for src in tests:
        _msg("BUILDING TEST", src)
        test = os.path.splitext(os.path.basename(src))[0]
        res = os.system('%s ../Build.py %s' % (PYTHON, test+".spec"))
        # Run the test in a clean environment to make sure they're really self-contained

        if run_executable:
            _msg("EXECUTING TEST", src)
            del os.environ["PATH"]
            res = os.system('dist%s%s%s.exe' % (test, os.sep, test))
            os.environ["PATH"] = path

        if res == 0:
            _msg("FINISHING TEST", src, short=1)
            counter["passed"].append(src)
        else:
            _msg("TEST", src, "FAILED", short=1)
            counter["failed"].append(src)
    print counter


if __name__ == '__main__':
    normal_tests = glob.glob('test*[0-9].py')
    interactive_tests = glob.glob('test*[0-9]i.py')

    from optparse import OptionParser
    parser = OptionParser(usage="%prog [options]")
    parser.add_option('-c', '--clean', action='store_true',
                      help='Clean up generated files')
    parser.add_option('-i', '--interactive-tests', action='store_true',
                      help='Run interactive tests (default: run normal tests)')
    parser.add_option('-n', '--no-run', action='store_true',
                      help='Do not run the built executables. '
                           'Useful for cross builds.')

    opts, args = parser.parse_args()
    if args:
        parser.error('Does not expect any arguments')

    if opts.clean:
        # only clean up
        clean()
        raise SystemExit()

    if opts.interactive_tests:
        print "Running interactive tests"
        tests = interactive_tests
    else:
        tests = normal_tests
        print "Running normal tests (-i for interactive tests)"

    clean()
    runtests(tests, run_executable=not opts.no_run)
