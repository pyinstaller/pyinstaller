#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

"""
OSX-specific test to check handling AppleEvents by bootloader
"""

# Library imports
# ---------------
import json
import os
import subprocess
import time

# Local imports
# -------------
from PyInstaller.utils.tests import importorskip, skipif_notosx


@skipif_notosx
def test_osx_custom_protocol_handler(tmpdir, pyi_builder_spec):
    tmpdir = str(tmpdir)  # Fix for Python 3.5
    app_path = os.path.join(tmpdir, 'dist',
                            'pyi_osx_custom_protocol_handler.app')
    logfile_path = os.path.join(tmpdir, 'dist', 'args.log')

    # Generate new URL scheme to avoid collisions
    custom_url_scheme = "pyi-test-%i" % time.time()
    os.environ["PYI_CUSTOM_URL_SCHEME"] = custom_url_scheme

    pyi_builder_spec.test_spec('pyi_osx_custom_protocol_handler.spec')

    # First run using 'open' registers custom protocol handler
    subprocess.check_call(['open', app_path])
    # 'open' starts program in a different process
    #  so we need to wait for it to finish
    time.sleep(2)

    # Call custom protocol handler
    url = custom_url_scheme + "://url-args"
    subprocess.check_call(['open', url])
    # Wait for the program to finish
    time.sleep(2)
    assert os.path.exists(logfile_path), 'Missing args logfile'
    with open(logfile_path, 'r') as fh:
        log_lines = fh.readlines()
    assert log_lines and log_lines[-1] == url, 'Invalid arg appended'


@skipif_notosx
@importorskip('PyQt5')
def test_osx_event_forwarding(tmpdir, pyi_builder_spec):
    tmpdir = str(tmpdir)  # Fix for Python 3.5
    app_path = os.path.join(tmpdir, 'dist',
                            'pyi_osx_event_forwarding.app')

    logfile_path = os.path.join(tmpdir, 'dist', 'events.log')

    # Generate unique URL scheme & file ext to avoid collisions
    unique_key = time.time()
    custom_url_scheme = "pyi-test-%i" % unique_key
    custom_file_ext = 'pyi_test_%i' % unique_key
    os.environ["PYI_CUSTOM_URL_SCHEME"] = custom_url_scheme
    os.environ["PYI_CUSTOM_FILE_EXT"] = custom_file_ext

    # test_script builds the app then implicitly runs the script, so we
    # pass arg "0" to tell the built script to exit right away here.
    pyi_builder_spec.test_spec('pyi_osx_event_forwarding.spec',
                               app_args=["0"])

    timeout = 60.0  # Give up after 60 seconds
    polltime = 0.25  # Poll events.log every 250ms

    def wait_for_started():
        t0 = time.time()  # mark start time
        # Poll logfile for app to be started (it writes "started" to the first
        # log line)
        while True:
            elapsed = time.time() - t0
            if elapsed > timeout:
                return
            if os.path.exists(logfile_path):
                with open(logfile_path) as fh:
                    log_lines = fh.readlines()
                    if log_lines:
                        first = log_lines[0]
                        assert first.startswith('started '), \
                            "Unexpected line in log file"
                        # Now, parse the logged args
                        # e.g. 'started {"argv": ["Arg1, ...]}'
                        dd = json.loads(first.split(" ", 1)[-1])
                        assert 'argv' in dd, "First line missing argv"
                        return dd['argv']  # it started ok, abort loop
            else:
                # Try again later
                time.sleep(polltime)

    # wait for the app started for us by test_spec to exit
    assert wait_for_started(), "App did not start"

    time.sleep(2)  # presumably app has exited after 2 seconds

    # clean up the log file created by test_spec() running the app
    os.remove(logfile_path)

    # Run using 'open', passing a 0-timeout as an arg.
    # macOS will auto-register the custom protocol handler and extension
    # association. Then app will quit immediately due to the "0" arg.
    subprocess.check_call(['open', app_path, '--args', "0"])

    assert wait_for_started(), 'App start timed out'
    time.sleep(2)  # wait for app to exit

    # App exited immediately, clean-up
    os.remove(logfile_path)

    # At this point both the protocol handler and the file ext are registered
    # 1. Try the file extension -- this tests the AppleEvent rewrite of
    #    a "file://" event to a regular filesystem path.

    # Create a file that is associated with this app
    assoc_path = os.path.join(tmpdir, 'dist', 'AFile.' + custom_file_ext)
    with open(assoc_path, 'wt') as fh:
        fh.write("Something\n")

    # Open app again by "open"ing the associated file.
    subprocess.check_call(['open', assoc_path])

    args = wait_for_started()
    assert args is not None, 'App start timed out'
    # Test the file path was received in argv via pre-startup translation of
    # file:// AppleEvent -> argv filesystem path.
    assert assoc_path in args, "File path was not received by app"

    # At this point the app is running.
    # 2. Call open again using the url associated with the app. This should
    #    forward the Apple URL event to the already-running app.
    url = custom_url_scheme + "://lowecase_required/hello_world"
    subprocess.check_call(['open', url])

    def wait_for_event_in_logfile():
        t0 = time.time()  # mark start time
        # Wait for the program to finish -- poll for expected line to appear
        # in events.log
        while True:
            assert os.path.exists(logfile_path), 'Missing events logfile'
            with open(logfile_path, 'rt') as fh:
                log_lines = fh.readlines()
            if len(log_lines) >= 2:
                assert log_lines[-1].strip().lower() == url.lower(), \
                    'Logged url does not match expected'
                return True
            else:
                # Try again later
                time.sleep(polltime)
            elapsed = time.time() - t0
            if elapsed > timeout:
                return False

    assert wait_for_event_in_logfile(), \
        'URL event did not appear in log before timeout'
