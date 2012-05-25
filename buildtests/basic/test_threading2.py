#
# Copyright (C) 2012, Martin Zibricky
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


# Test bootloader behaviour for threading code.
# Default behaviour of Python interpreter is to wait for all threads
# before exiting main process.
# Bootloader should behave also this way.


import os
import subprocess
import sys
import threading


_OUT_EXPECTED = ['ONE', 'TWO', 'THREE']


# Code for the subprocess.
if 'PYI_THREAD_TEST_CASE' in os.environ:
    class TestThreadClass(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)

        def run(self):
            print 'ONE'
            print 'TWO'
            print 'THREE'
    # Main process should not exit before the thread stops.
    # This is the behaviour of Python interpreter.
    TestThreadClass().start()


# Execute itself in a subprocess.
else:
    # Differenciate subprocess code.
    itself = sys.argv[0]
    # Run subprocess.
    proc = subprocess.Popen([itself], stdout=subprocess.PIPE,
            env={'PYI_THREAD_TEST_CASE': 'any_string'},
            stderr=subprocess.PIPE, shell=False)
    # Waits for subprocess to complete.
    out, err = proc.communicate()

    # Make output from subprocess visible.
    print out

    # Check output.
    if out.splitlines() != _OUT_EXPECTED:
        raise SystemExit('Subprocess did not print ONE, TWO, THREE in correct order.')
