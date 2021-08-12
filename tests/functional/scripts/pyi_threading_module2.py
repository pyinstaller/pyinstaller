#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Test bootloader behavior for threading code. The default behavior of Python interpreter is to wait for all threads
# before exiting the main process. Bootloader should behave in the same way.

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

    # Main process should not exit before the thread stops. This is the behaviour of Python interpreter.
    TestThreadClass().start()

# Execute itself in a subprocess.
else:
    # Differenciate subprocess code.
    itself = sys.argv[0]
    # Run subprocess.
    import subprocess

    # Preserve environment to avoid `Failed to initialize Windows random API (CryptoGen)`
    env = dict(os.environ)
    env['PYI_THREAD_TEST_CASE'] = 'yes'

    proc = subprocess.Popen([itself], stdout=subprocess.PIPE, env=env, stderr=subprocess.PIPE, shell=False)
    # Waits for subprocess to complete.
    out, err = proc.communicate()

    # Make output from subprocess visible.
    print(out)
    out = out.decode('ascii')
    print(out)

    # Remove empty lines from output.
    out = out.strip().splitlines()
    for line in out:
        if not line.strip():  # Empty line detected.
            out.remove(line)
    # Check output.
    if out != _OUT_EXPECTED:
        print(" +++++++ SUBPROCESS ERROR OUTPUT +++++++")
        print(err)
        raise SystemExit(
            'Subprocess did not print ONE, TWO, THREE in correct order. (output was %r, return code was %s)' %
            (out, proc.returncode)
        )
