# ----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# ----------------------------------------------------------------------------

import os
import sys
import pytest

from PyInstaller.compat import is_win

START_METHODS = ['spawn'] if is_win else ['spawn', 'fork', 'forkserver']


@pytest.mark.timeout(timeout=60)
@pytest.mark.parametrize("start_method", START_METHODS)
def test_multiprocessing_process(pyi_builder, start_method):
    pyi_builder.test_script("pyi_multiprocessing_process.py", app_args=[start_method])


@pytest.mark.timeout(timeout=60)
@pytest.mark.parametrize("start_method", START_METHODS)
def test_multiprocessing_queue(pyi_builder, start_method):
    pyi_builder.test_script("pyi_multiprocessing_queue.py", app_args=[start_method])


@pytest.mark.timeout(timeout=60)
@pytest.mark.parametrize("start_method", START_METHODS)
def test_multiprocessing_pool(pyi_builder, start_method):
    pyi_builder.test_script("pyi_multiprocessing_pool.py", app_args=[start_method])


@pytest.mark.timeout(timeout=60)
@pytest.mark.parametrize("start_method", START_METHODS)
def test_multiprocessing_semaphore(pyi_builder, start_method, capfd):
    pyi_builder.test_script("pyi_multiprocessing_semaphore.py", app_args=[start_method])

    out, err = capfd.readouterr()

    # Print the captured output and error so that it will show up in the test output.
    sys.stderr.write(err)
    sys.stdout.write(out)

    expected = ["In main", "In subprocess"]

    assert os.linesep.join(expected) in out
    for substring in expected:
        assert out.count(substring) == 1


# Test that we can start `multiprocessing.Process` in thread-safe manner concurrently, from multiple threads at (almost)
# the same time. See #7410.
@pytest.mark.timeout(timeout=60)
@pytest.mark.parametrize("start_method", START_METHODS)
def test_multiprocessing_process_start_in_threads(pyi_builder, start_method):
    pyi_builder.test_script("pyi_multiprocessing_process_start_in_threads.py", app_args=[start_method])
