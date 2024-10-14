# -*- coding: utf-8 -*-
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

import sys
import signal
import subprocess

import pytest


@pytest.mark.darwin
@pytest.mark.linux
@pytest.mark.parametrize('forward_signals', [True, False], ids=['forward', 'ignore'])
@pytest.mark.parametrize('pyi_builder', ['onefile'], indirect=True)  # Run only in onefile mode.
def test_onefile_signal_handling(pyi_builder, forward_signals):
    # Build the test program. The `pyi_builder.test_soruce` also runs the built program, but since no arguments are
    # passed via command-line, this program run is a no-op.
    pyi_builder.test_source(
        """
        import os
        import sys
        import signal
        import time

        # Quietly exit if no signal number is given on command-line. This accommodates the fact that
        # `pyi_builder.test_source()` always runs the program after building it.
        if len(sys.argv) < 2:
            print(f"Usage: {sys.argv[0]} <signal-number>", file=sys.stderr)
            sys.exit(0)

        # Signal number is passed as first command-line argument
        signal_number = int(sys.argv[1])
        signal_name = signal.Signals(signal_number).name  # This implicitly validates signal number

        # Return code: received signal number, or zero if signal was not received.
        return_code = 0

        # Install signal handler
        def signal_handler(signum, *args):
            global return_code
            return_code = signum  # Set program's return code to signal number

        print(f"Installing signal handler for signal={signal_number} ({signal_name})", file=sys.stderr)
        signal.signal(signal_number, signal_handler)

        # Send signal to parent process of the onefile frozen application.
        parent_pid = os.getppid()
        print(
            f"Sending signal={signal_number} ({signal_name}) to parent process with PID={parent_pid}",
            file=sys.stderr,
        )
        os.kill(parent_pid, signal_number)

        # Wait up to a second for signal to be delivered.
        for i in range(10):
            if return_code != 0:
                print("Signal received!", file=sys.stderr)
                break
            time.sleep(0.1)
        else:
            print("Signal not received!", file=sys.stderr)

        sys.exit(return_code)
        """,
        pyi_args=[] if forward_signals else ['--bootloader-ignore-signals'],
    )

    exes = pyi_builder._find_executables('test_source')
    assert len(exes) == 1
    program_exe = exes[0]

    # Use the built executable with all applicable signals.
    failures = []
    for signal_entry in signal.Signals:
        signal_name = signal_entry.name
        signal_number = signal_entry.value

        # Exemptions
        reason = None
        if signal_name in {'SIGKILL', 'SIGSTOP'}:
            reason = f"{signal_name} cannot be caught."
        elif signal_name in {'SIGCHLD', 'SIGCLD'}:
            reason = f"{signal_name} is not handled by bootloader: required for wait() on child process."
        elif signal_name == 'SIGTSTP':
            reason = f"{signal_name} is not handled by bootloader: required for Ctrl-Z."

        if reason is not None:
            print(f"=== skipping test with {signal_name}: {reason} ===", file=sys.stderr)
            continue

        # Expected return code: signal number in signal-forwarding mode, zero otherwise.
        expected_code = signal_number if forward_signals else 0

        # Run
        print(f"=== running test with {signal_name} ===", file=sys.stderr)
        status = subprocess.run([program_exe, str(signal_number)])
        ret_code = status.returncode

        print(f"=== program returned code {ret_code} (expected {expected_code}) ===", file=sys.stderr)
        if ret_code != expected_code:
            failures.append((signal_name, f"Unexpected exit code: {ret_code} (expected={expected_code})!"))

    assert not failures, "Not all signals were handled as expected!"
