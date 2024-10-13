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

import signal

import pytest


@pytest.mark.darwin
@pytest.mark.linux
@pytest.mark.parametrize(
    'signal_name',
    [sig.name for sig in signal.Signals],
)
@pytest.mark.parametrize('forward_signals', [True, False], ids=['forward', 'ignore'])
@pytest.mark.parametrize('pyi_builder', ['onefile'], indirect=True)  # Run only in onefile mode.
def test_onefile_signal_handling(pyi_builder, signal_name, forward_signals):
    if signal_name in {'SIGKILL', 'SIGSTOP'}:
        pytest.skip(f"{signal_name} cannot be caught.")
    elif signal_name in {'SIGCHLD', 'SIGCLD'}:
        pytest.skip(f"{signal_name} is not handled by bootloader: required for wait() on child process.")
    elif signal_name == 'SIGTSTP':
        pytest.skip(f"{signal_name} is not handled by bootloader: required for Ctrl-Z.")

    signal_number = signal.Signals[signal_name].value  # Convert signal name to signal number for easier handling.

    pyi_builder.test_source(
        """
        import os
        import sys
        import signal
        import time

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
        app_args=[str(signal_number)],
        retcode=signal_number if forward_signals else 0,
    )
