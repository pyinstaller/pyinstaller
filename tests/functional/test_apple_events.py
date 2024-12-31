#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
macOS-specific test to check handling of Apple Events in the bootloader.
"""

import json
import os
import subprocess
import time
import functools
import uuid

import pytest

from PyInstaller.compat import is_macos_11


# On macOS 11, the custom URL schema registration does not work properly if the .app bundle is located in the default
# temporary path (/var or /private/var prefix). Therefore, for the tests below to work, the pytest's base temporary
# path needs to be moved (for example, via the --basetemp argument).
def macos11_check_tmp_path(test):
    @functools.wraps(test)
    def wrapped(**kwargs):
        tmp_path = kwargs['tmp_path']
        if is_macos_11 and str(tmp_path).startswith(('/var', '/private/var')):
            pytest.skip(
                "The custom URL schema registration does not work on macOS 11 when .app bundles are placed in "
                "the default temporary path."
            )
        return test(**kwargs)

    return wrapped


# This test function is similar to the former test_osx_event_forwarding, but is designed to test onefile vs onedir
# builds, with argv_emu on and off. It is also designed to be used with different Apple Event loggers based on
# different toolkits: Carbon via ctypes, tkinter, PyQt5, provided the logger implements the common log file format.
#
# However, in practice, in turns out that each high-level toolkit handles events a bit differently, and offers different
# level of support (in tkinter/Tk case even depending on the Tk version). Therefore, this test function is currently
# used only with Carbon-based logger and does not (yet) implement toolkit-specific quirks.
def _test_apple_events_handling(appname, tmp_path, pyi_builder_spec, monkeypatch, build_mode, argv_emu):
    # Helper for determining application start/finish via logged events.
    def wait_for_event(logfile, event, timeout=60, polltime=0.25):
        """
        Wait for the log file with 'started' or 'finished' entry to appear.
        """
        assert event in {'started', 'finished'}, f"Invalid event: {event}!"
        t0 = time.time()  # mark start time
        # Poll logfile for desired event (the app writes 'started' at beginning and 'finished' at the end).
        while True:
            elapsed = time.time() - t0
            if elapsed > timeout:
                return False
            if os.path.exists(logfile_path):
                with open(logfile_path, 'r', encoding='utf8') as fh:
                    log_lines = fh.readlines()
                    if log_lines:
                        if event == 'started':
                            first = log_lines[0]
                            assert first.startswith('started '), "Unexpected line in log file!"
                            return True
                        elif log_lines[-1].startswith('finished '):
                            return True
            # Try again later
            time.sleep(polltime)

    # Generate unique URL scheme & file ext to avoid collisions.
    unique_key = uuid.uuid4()
    custom_url_scheme = f"pyi-test-{unique_key}"
    custom_file_ext = f"pyi_test_{unique_key}"
    monkeypatch.setenv("PYI_CUSTOM_URL_SCHEME", custom_url_scheme)
    monkeypatch.setenv("PYI_CUSTOM_FILE_EXT", custom_file_ext)
    monkeypatch.setenv("PYI_BUILD_MODE", build_mode)
    monkeypatch.setenv("PYI_ARGV_EMU", str(int(argv_emu)))

    logfile_path = tmp_path / 'dist' / 'events.log'

    # test_spec() builds the app and automatically runs it. As we want to test custom protocol handler registration, we
    # want this run to exit as soon as possible. Passing arg "0" would have it exit immediately, but with some logger
    # applications (e.g., pure Carbon based), that prevents bundle's executable to be found on subsequent open attempts;
    # presumably because event loop does not process any events. So use 5-seconds timeout instead.
    pyi_builder_spec.test_spec(f'{appname}.spec', app_args=["5"])

    # Wait for the app started by test_spec() to exit
    assert wait_for_event(logfile_path, 'started'), 'Timeout while waiting for app to start (test_spec run)!'
    assert wait_for_event(logfile_path, 'finished'), 'Timeout while waiting for app to finish (test_spec run)!'
    time.sleep(5)  # wait for app to fully exit

    # Clean up the log file created by test_spec() running the app
    os.remove(logfile_path)

    # Rename the dist directory into dist-{uuid}, to ensure path uniqueness for each test run. The name of the temporary
    # directory may be the same across different test runs (with different parametrizations) due to the length of the
    # test name; re-using the same path (even though the preceding test's contents were removed) may cause issues with
    # app bundle registration...
    old_dist = tmp_path / 'dist'
    new_dist = tmp_path / f'dist-{unique_key}'

    old_dist.rename(new_dist)

    app_path = new_dist / f'{appname}.app'
    logfile_path = new_dist / 'events.log'

    # Run using 'open', passing a 5-second timeout as an arg to exit as soon as possible (do not pass 0 to prevent
    # skipping the event loop in the application). This will cause macOS to register the custom protocol handler and
    # file extension association.
    subprocess.check_call(['open', str(app_path), '--args', "5"])

    assert wait_for_event(logfile_path, 'started'), 'Timeout while waiting for app to start (registration run)!'
    assert wait_for_event(logfile_path, 'finished'), 'Timeout while waiting for app to finish (registration run)!'
    time.sleep(5)  # wait for app to fully exit

    # App exited immediately, clean-up
    logfile_path.unlink()

    # At this point both the protocol handler and the file ext are registered
    # 1. Try the file extension -- this tests the AppleEvent rewrite of a "file://" event to a regular filesystem path.

    # Create 32 files that are associated with this app. This tests the robustness of the argv-emu by spamming it with
    # lots of args and seeing what happens.
    n_files = 32
    assoc_files = []
    for idx in range(n_files):
        assoc_path = tmp_path / f'AFile{idx}.{custom_file_ext}'
        assoc_path.write_text(f"File contents #{idx}\n", encoding='utf-8')
        assoc_files.append(str(assoc_path))

    # Open app again by "open"ing the associated files.
    #
    # These are sent as Apple Events to the app immediately after it starts; if argv emulation is enabled, the
    # bootloader processes these events and translates them into file paths, passing them as argv to the
    # subordinate app.
    #
    # The generator below produces odd numbered files as "file://" URLs, and even numbered are just file paths. Under
    # argv emulation, they should all end up appended to sys.argv in the app as simple file paths.
    files_list = [('file://' if idx % 2 else '') + file_path for idx, file_path in enumerate(assoc_files)]
    subprocess.check_call(['open', *files_list])

    assert wait_for_event(logfile_path, 'started'), 'Timeout while waiting for app to start (test run)!'

    # At this point the app is running.

    # 2. Call open using the url associated with the app. This should forward the Apple URL event to the running app.
    url_hello = f"{custom_url_scheme}://lowecase_required/hello_world/"
    subprocess.check_call(['open', url_hello])
    time.sleep(1.0)

    # 3. Put application into background so that we can re-activate it. Taken from the former test_osx_event_forwarding
    # that used PyQt5, in case we ever try to use this test function with PyQt5-based logger.
    app_put_to_background = False
    try:
        # On GitHub Actions macos-11 runner, launching osascript sometimes fails with the following error:
        # "osascript: can't open default scripting component."
        subprocess.check_call(['osascript', "-e", 'tell application "System Events" to activate'])
        app_put_to_background = True
    except Exception:
        pass
    time.sleep(1.0)  # delay for above applescript

    if app_put_to_background:
        # The app is running now, in the background, and does not have focus.

        # 4. Call open passing the app path again -- this should activate the already-running app.
        subprocess.check_call(['open', app_path])
        time.sleep(1.0)  # the activate event gets sent with a delay

    # 5. Call open with first four associated files.
    files_list = [('file://' if idx % 2 else '') + file_path for idx, file_path in enumerate(assoc_files[:4])]
    subprocess.check_call(['open', *files_list])
    time.sleep(1.0)

    # 6. Call open again using the url associated with the app. This should forward the Apple URL event to the
    # already-running app.
    url_goodbye = f"{custom_url_scheme}://lowecase_required/goodybe_galaxy/"
    subprocess.check_call(['open', url_goodbye])
    time.sleep(1.0)

    # 7. Call open again using the url associated with the app, this time testing support for large URL data (~64kB).
    url_large = f"{custom_url_scheme}://lowecase_required/large_data/"
    # Note: We would have gone larger but 'open' itself seems to not consistently like data over a certain size.
    url_large += 'x' * 64000  # Append 64 kB of data to URL to stress-test.
    subprocess.check_call(['open', url_large])
    time.sleep(1.0)

    # 8. Call open with last four associated files again.
    files_list = [('file://' if idx % 2 else '') + file_path for idx, file_path in enumerate(assoc_files[-4:])]
    subprocess.check_call(['open', *files_list])
    time.sleep(1.0)

    # 9. Wait for application to finish.
    assert wait_for_event(logfile_path, 'finished'), 'Timeout while waiting for app to finish (test run)!'
    time.sleep(2)  # wait for app to fully exit

    # *** Analyze the contents of the log file ***
    with open(logfile_path, 'r', encoding='utf8') as fh:
        log_lines = fh.readlines()

    assert log_lines[0].startswith('started '), "Unexpected first line in log!"
    assert log_lines[-1].startswith('finished '), "Unexpected last line in log!"

    events = []
    errors = []
    unknown = []
    for log_line in log_lines[1:-1]:
        if log_line.startswith('ae '):
            # (raw) Apple Event
            _, event_id, event_data = log_line.split(" ", 2)
            events.append((event_id, json.loads(event_data)))
        elif log_line.startswith('ERROR '):
            errors.append(log_line.split(" ", 1))
        else:
            unknown.append(log_line)

    assert not errors, "Event log contains error(s)!"
    assert not unknown, "Event log contains unknown line(s)!"

    # First line: application start - read arguments.
    data = json.loads(log_lines[0].split(" ", 1)[-1])
    args = data['args']  # Validated below, with initial event.

    # Last line: application finish - read activation count.
    data = json.loads(log_lines[-1].split(" ", 1)[-1])
    activation_count = data['activation_count']

    # Event: initial event
    #
    # In onefile builds, we always receive oapp event, regardless of how application was opened (e.g., via odoc or
    # GURL), because the actual opening event is received by the parent process, whereas child is independent and
    # is always launched via "normal" open (oapp). Therefore, having the argv-emu enabled or not also has no effect on
    # the initial oapp event in onefile mode.
    #
    # In onedir mode without argv emulation, we receive either oapp for normal open, or odoc/GURL if launched via open
    # document/URL. The test run begins with an open-file request, so the initial event should be an odoc one.
    #
    # When argv-emu is enabled in onedir mode, the argv-emu event loop swallows that initial event, whatever it may have
    # been. To make up for it and prevent issues with some toolkits (e.g., Tcl/Tk), it emits a fake oapp event.
    initial_oapp = True  # expect initial oapp event
    if build_mode == 'onedir' and not argv_emu:
        initial_oapp = False  # initial event is odoc

    event_idx = 0

    if initial_oapp:
        event, data = events[event_idx]
        event_idx += 1
        assert event == 'oapp'

    # Validate arguments received at application start via argv.
    if argv_emu:
        # argv-emu; we expect whole list of files in arguments
        assert args == assoc_files, "Arguments received via argv-emu do not match expected list!"
    else:
        # No argv-emu; args should be empty (in particular, the -psn_* arg should be filtered out).
        assert args == [], "Application should receive no arguments when argv-emu is disabled!"

        # The open-file request should be received as odoc request instead. Might be very first event, or might follow
        # an oapp, depending on the build_mode.
        event, data = events[event_idx]
        event_idx += 1
        assert event == 'odoc'
        assert data == assoc_files

    # Validate activation count at the time of finish. One contribution should be from the initial oapp event (if
    # applicable), and one from re-activation when we sent application to background and then called it forward
    # (provided there was no osascript error).
    expected_activations = initial_oapp + app_put_to_background
    assert activation_count == expected_activations, "Application did not handle activation event(s) as expected!"

    # The rest of events should be received normally, regardless of argv-emu. Either directly (onedir), or via the
    # forwarding mechanism (onefile).

    # Event: GURL with single URL (url_hello)
    event, data = events[event_idx]
    event_idx += 1
    assert event == 'GURL'
    assert data == [url_hello]

    # Event: rapp (re-activation)
    # Applicable only if we successfully put application to background via osascript
    if app_put_to_background:
        event, data = events[event_idx]
        event_idx += 1
        assert event == 'rapp'

    # Event: odoc with first 4 files
    event, data = events[event_idx]
    event_idx += 1
    assert event == 'odoc'
    assert data == assoc_files[:4]

    # Event: GURL with single URL (url_goodbye)
    event, data = events[event_idx]
    event_idx += 1
    assert event == 'GURL'
    assert data == [url_goodbye]

    # Event: GURL with single large-data URL (url_large)
    event, data = events[event_idx]
    event_idx += 1
    assert event == 'GURL'
    assert data == [url_large]

    # Event: odoc with last 4 files
    event, data = events[event_idx]
    event_idx += 1
    assert event == 'odoc'
    assert data == assoc_files[-4:]

    # *** Cleanup ***
    # Delete all the temp files to be polite
    for ff in assoc_files:
        try:
            os.remove(ff)
        except OSError:
            pass


@pytest.mark.darwin
@macos11_check_tmp_path
@pytest.mark.flaky(reruns=3)
@pytest.mark.parametrize("build_mode", ['onefile', 'onedir'])
@pytest.mark.parametrize("argv_emu", [True, False], ids=["emu", "noemu"])
def test_apple_event_handling_carbon(tmp_path, pyi_builder_spec, monkeypatch, build_mode, argv_emu):
    # Carbon-based event logger.
    return _test_apple_events_handling(
        'pyi_osx_aevent_handling_carbon',
        tmp_path,
        pyi_builder_spec,
        monkeypatch,
        build_mode,
        argv_emu,
    )
