#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
OSX-specific test to check handling AppleEvents by bootloader.
"""

import json
import os
import subprocess
import time
import functools

import pytest

from PyInstaller.utils.tests import importorskip
from PyInstaller.compat import is_macos_11


# On macOS 11, the custom URL schema registration does not work properly if the .app bundle is located in the default
# temporary path (/var or /private/var prefix). Therefore, for the tests below to work, the pytest's base temporary
# path needs to be moved (for example, via the --basetemp argument).
def macos11_check_tmpdir(test):
    @functools.wraps(test)
    def wrapped(**kwargs):
        tmpdir = kwargs['tmpdir']
        if is_macos_11 and str(tmpdir).startswith(('/var', '/private/var')):
            pytest.skip(
                "The custom URL schema registration does not work on macOS 11 when .app bundles are placed in "
                "the default temporary path."
            )
        return test(**kwargs)

    return wrapped


@pytest.mark.darwin
@macos11_check_tmpdir
@pytest.mark.parametrize("mode", ['onefile'])
def test_osx_custom_protocol_handler(tmpdir, pyi_builder_spec, monkeypatch, mode):
    app_path = os.path.join(tmpdir, 'dist', 'pyi_osx_custom_protocol_handler.app')
    logfile_path = os.path.join(tmpdir, 'dist', 'args.log')

    # Generate new URL scheme to avoid collisions
    custom_url_scheme = "pyi-test-%i" % time.time()
    monkeypatch.setenv("PYI_CUSTOM_URL_SCHEME", custom_url_scheme)
    monkeypatch.setenv("PYI_BUILD_MODE", mode)

    pyi_builder_spec.test_spec('pyi_osx_custom_protocol_handler.spec')

    # First run using 'open' registers custom protocol handler
    subprocess.check_call(['open', app_path])
    # 'open' starts program in a different process so we need to wait for it to finish
    time.sleep(5)

    # Call custom protocol handler
    url = custom_url_scheme + "://url-args"
    subprocess.check_call(['open', url])
    # Wait for the program to finish
    time.sleep(5)
    assert os.path.exists(logfile_path), 'Missing args logfile'
    with open(logfile_path, 'r') as fh:
        log_lines = fh.readlines()
    assert log_lines and log_lines[-1] == url, 'Invalid arg appended'


@pytest.mark.darwin
@macos11_check_tmpdir
@importorskip('PyQt5')
@pytest.mark.parametrize("mode", ['onefile'])
def test_osx_event_forwarding(tmpdir, pyi_builder_spec, monkeypatch, mode):
    app_path = os.path.join(tmpdir, 'dist', 'pyi_osx_event_forwarding.app')

    logfile_path = os.path.join(tmpdir, 'dist', 'events.log')

    # This test requires the default (windowed) display backend, so reset any QT_QPA_PLATFORM override.
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)

    # Generate unique URL scheme & file ext to avoid collisions
    unique_key = int(time.time())
    custom_url_scheme = "pyi-test-%i" % unique_key
    custom_file_ext = 'pyi_test_%i' % unique_key
    monkeypatch.setenv("PYI_CUSTOM_URL_SCHEME", custom_url_scheme)
    monkeypatch.setenv("PYI_CUSTOM_FILE_EXT", custom_file_ext)
    monkeypatch.setenv("PYI_BUILD_MODE", mode)

    # test_script builds the app then implicitly runs the script, so we pass arg "0" to tell the built script to exit
    # right away here.
    pyi_builder_spec.test_spec('pyi_osx_event_forwarding.spec', app_args=["0"])

    timeout = 60.0  # Give up after 60 seconds
    polltime = 0.25  # Poll events.log every 250ms

    def wait_for_started():
        t0 = time.time()  # mark start time
        # Poll logfile for app to be started (it writes "started" to the first log line)
        while True:
            elapsed = time.time() - t0
            if elapsed > timeout:
                return
            if os.path.exists(logfile_path):
                with open(logfile_path) as fh:
                    log_lines = fh.readlines()
                    if log_lines:
                        first = log_lines[0]
                        assert first.startswith('started '), "Unexpected line in log file"
                        # Now, parse the logged args. e.g. 'started {"argv": ["Arg1, ...]}'
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

    # Run using 'open', passing a 0-timeout as an arg. macOS will auto-register the custom protocol handler and
    # extension association. Then app will quit immediately due to the "0" arg.
    subprocess.check_call(['open', app_path, '--args', "0"])

    assert wait_for_started(), 'App start timed out'
    time.sleep(2)  # wait for app to exit

    # App exited immediately, clean-up
    os.remove(logfile_path)

    # At this point both the protocol handler and the file ext are registered
    # 1. Try the file extension -- this tests the AppleEvent rewrite of a "file://" event to a regular filesystem path.

    # Create 32 files that are associated with this app. This tests the robustness of the argv-emu by spamming it with
    # lots of args and seeing what happens.
    n_files = 32
    assoc_files = []
    for ii in range(n_files):
        assoc_path = os.path.join(tmpdir, 'dist', 'AFile{}.{}'.format(ii, custom_file_ext))
        with open(assoc_path, 'wt') as fh:
            fh.write("File contents #{}\n".format(ii))
        assoc_files.append(assoc_path)

    # Open app again by "open"ing the associated files.
    #
    # These are sent as Apple Events to the app immediately after it starts, which the bootloader translates back into
    # file paths at startup, passing them as argv to the subordinate app.
    #
    # The generator below produces odd numbered files as "file://" URLs, and even numbered are just file paths. They all
    # should end up appended to sys.argv in the app as simple file paths.
    subprocess.check_call(['open', *[('file://' if ii % 2 else '') + ff for ii, ff in enumerate(assoc_files)]])

    args = wait_for_started()
    assert args is not None, 'App start timed out'
    # Test that all the file paths were received in argv via pre-startup translation of file:// AppleEvent -> argv
    # filesystem path.
    assert assoc_files == args[1:], "An expected file path was not received by the app"

    # At this point the app is running.

    # This is a trick to make our app lose focus so that Qt forwards the "Activated" events properly to our event
    # handler in pyi_pyqt5_log_events.py
    subprocess.check_call(['osascript', "-e", 'tell application "System Events" to activate'])
    time.sleep(1.0)  # delay for above applescript

    # The app is running now, in the background, and doesn't have focus

    # 2. Call open passing the app path again -- this should activate the already-running app and the activation_count
    #    should be 2 after it exits.
    subprocess.check_call(['open', app_path])
    time.sleep(1.0)  # the activate event gets sent with a delay

    # 3. Call open again using the url associated with the app. This should forward the Apple URL event to the
    #    already-running app.
    url = custom_url_scheme + "://lowecase_required/hello_world/"
    # Test support for large URL data ~64KB. Note: We would have gone larger but 'open' itself seems to not consistently
    # like data over a certain size.
    url += 'x' * 64000  # Append 64 KB of data to URL to stress-test
    subprocess.check_call(['open', url])
    activation_count = None

    def wait_for_event_in_logfile():
        t0 = time.time()  # mark start time
        # Wait for the program to finish -- poll for expected line to appear in events.log
        while True:
            assert os.path.exists(logfile_path), 'Missing events logfile'
            with open(logfile_path, 'rt') as fh:
                log_lines = fh.readlines()
            if len(log_lines) >= 3:
                url_line = log_lines[1]
                activation_line = log_lines[2]
                assert url_line.startswith("url ")
                assert activation_line.startswith("activate_count ")
                url_part = url_line.split(" ", 1)[-1]
                assert url_part.strip().lower() == url.lower(), 'Logged url does not match expected'
                activation_part = activation_line.split(" ", 1)[-1]
                nonlocal activation_count
                activation_count = int(activation_part.strip())
                return True
            else:
                # Try again later
                time.sleep(polltime)
            elapsed = time.time() - t0
            if elapsed > timeout:
                return False

    assert wait_for_event_in_logfile(), 'URL event did not appear in log before timeout'

    assert activation_count == 2, "App did not receive rapp (re-Open app) event properly"

    # Delete all the temp files to be polite
    for ff in assoc_files:
        try:
            os.remove(ff)
        except OSError:
            pass
