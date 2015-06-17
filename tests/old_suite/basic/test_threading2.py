#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Test bootloader behaviour for threading code.
# Default behaviour of Python interpreter is to wait for all threads
# before exiting main process.
# Bootloader should behave also this way.


import os
import sys
import threading


_OUT_EXPECTED = ['ONE', 'TWO', 'THREE']


# Code for the subprocess.
if 'PYI_THREAD_TEST_CASE' in os.environ:
    class TestThreadClass(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)

        def run(self):
            print('ONE')
            print('TWO')
            print('THREE')
    # Main process should not exit before the thread stops.
    # This is the behaviour of Python interpreter.
    TestThreadClass().start()


# Execute itself in a subprocess.
else:
    # Differenciate subprocess code.
    itself = sys.argv[0]
    # Run subprocess.
    try:
        import subprocess
        proc = subprocess.Popen([itself], stdout=subprocess.PIPE,
                env={'PYI_THREAD_TEST_CASE': 'any_string'},
                stderr=subprocess.PIPE, shell=False)
        # Waits for subprocess to complete.
        out, err = proc.communicate()
    except ImportError:
        # Python 2.3 does not have subprocess module.
        command = 'PYI_THREAD_TEST_CASE=any_string ' + itself
        pipe = os.popen(command)
        out = pipe.read()
        pipe.close()

    # Make output from subprocess visible.
    print(out)

    # Remove empty lines from output.
    out = out.strip().splitlines()
    for line in out:
        if not line.strip():  # Empty line detected.
            out.remove(line)
    # Check output.
    if out != _OUT_EXPECTED:
        raise SystemExit('Subprocess did not print ONE, TWO, THREE in correct order.')
