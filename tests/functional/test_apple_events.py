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

    if os.path.exists(logfile_path):
        os.remove(logfile_path)
    assert not os.path.exists(logfile_path), 'Events logfile still exists!'

    # Generate new URL scheme to avoid collisions
    custom_url_scheme = "pyi-test-%i" % time.time()
    os.environ["PYI_CUSTOM_URL_SCHEME"] = custom_url_scheme

    pyi_builder_spec.test_spec('pyi_osx_event_forwarding.spec')

    timeout = 10.0  # Give up after 10 seconds
    polltime = 0.25  # Poll events.log every 250ms

    # Run using 'open', passing the timeout as an arg (side-effect: registers
    # custom protocol handler)
    subprocess.check_call(['open', app_path, '--args', str(timeout)])

    def wait_for_started():
        t0 = time.time()  # mark start time
        # Poll logfile for app to be started (it writes "started" to the first
        # log line)
        while True:
            elapsed = time.time() - t0
            if elapsed > timeout:
                return False
            if os.path.exists(logfile_path):
                with open(logfile_path) as fh:
                    log_lines = fh.readlines()
                    if log_lines:
                        assert log_lines[0].startswith('started'), \
                            "Unexpected line in log file"
                        return True  # it started ok, abort loop
            else:
                # Try again later
                time.sleep(polltime)

    assert wait_for_started(), 'App start timed out'

    # At this point the app is running,
    # Calling open again using the url should forward the Apple URL event to
    # the already-running app.
    url = custom_url_scheme + "://AnEvent"
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
                assert log_lines[-1].strip() == url, \
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
