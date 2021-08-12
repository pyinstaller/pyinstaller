#-----------------------------------------------------------------------------
# Copyright (c) 2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Test for unbuffered stdio (stdout/stderr) mode.
"""

import os
import asyncio

import pytest

from PyInstaller.compat import is_py37, is_win


@pytest.mark.skipif(
    os.environ.get('CI', 'false').lower() == 'true',
    reason="The test does not support CI (pytest-xdist sometimes runs it in secondary thread)."
)
@pytest.mark.parametrize('stream_mode', ['binary', 'text'])
@pytest.mark.parametrize('output_stream', ['stdout', 'stderr'])
def test_unbuffered_stdio(tmp_path, output_stream, stream_mode, pyi_builder_spec):
    # Unbuffered text layer was introduced in Python 3.7
    if stream_mode == 'text' and not is_py37:
        pytest.skip("Unbuffered text layer of stdout and stderr streams requires Python 3.7 or later.")

    # Freeze the test program; test_spec() builds the app and runs it, so explicitly set the number of
    # stars to 0 for this run.
    pyi_builder_spec.test_spec('pyi_unbuffered_output.spec', app_args=['--num-stars', '0'])

    # Path to the frozen executable
    executable = os.path.join(tmp_path, 'dist', 'pyi_unbuffered_output', 'pyi_unbuffered_output')

    # Expected number of stars
    EXPECTED_STARS = 5

    # Run the test program via asyncio.SubprocessProtocol and monitor the output.
    class SubprocessDotCounter(asyncio.SubprocessProtocol):
        def __init__(self, loop, output='stdout'):
            self.count = 0
            self.loop = loop
            # Select stdout vs stderr
            assert output in {'stdout', 'stderr'}
            self.out_fd = 1 if output == 'stdout' else 2

        def pipe_data_received(self, fd, data):
            if fd == self.out_fd:
                # Treat any data batch that does not end with the * as irregularity
                if not data.endswith(b'*'):
                    return
                self.count += data.count(b'*')

        def connection_lost(self, exc):
            self.loop.stop()  # end loop.run_forever()

    # Create event loop
    if is_win:
        loop = asyncio.ProactorEventLoop()  # for subprocess' pipes on Windows
    else:
        loop = asyncio.SelectorEventLoop()
    asyncio.set_event_loop(loop)

    counter_proto = SubprocessDotCounter(loop, output=output_stream)

    # Run
    try:
        proc = loop.subprocess_exec(
            lambda: counter_proto,
            executable,
            "--num-stars", str(EXPECTED_STARS),
            "--output-stream", output_stream,
            "--stream-mode", stream_mode
        )  # yapf: disable
        loop.run_until_complete(proc)
        loop.run_forever()
    finally:
        loop.close()

    # Check the number of received stars
    assert counter_proto.count == EXPECTED_STARS
