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


# Test that we can start a nested `multiprocessing.Process` from within a `multiprocessing.Process`. See #7494.
# Nested multi-processing is broken in Python 3.11.5 because SemLock.is_fork_ctx attribute (added in
# https://github.com/python/cpython/commit/34ef75d3ef559288900fad008f05b29155eb8b59) is not properly
# serialized/deserialized.
@pytest.mark.timeout(timeout=60)
@pytest.mark.parametrize("start_method", START_METHODS)
@pytest.mark.xfail(sys.version_info[:3] == (3, 11, 5), reason="Python 3.11.5 broke nested multiprocessing.")
def test_multiprocessing_nested_process(pyi_builder, start_method):
    pyi_builder.test_script("pyi_multiprocessing_nested_process.py", app_args=[start_method])


# Test that we are able to retrieve the code object for `__main__` module in the sub-process.
# NOTE: in unfrozen version, this works only with `fork` start method. However, in current `multiprocessing` support,
# it should work with all start methods when frozen.
@pytest.mark.timeout(timeout=60)
@pytest.mark.parametrize("start_method", START_METHODS)
def test_multiprocessing_main_module_code_in_process(pyi_builder, start_method):
    pyi_builder.test_script("pyi_multiprocessing_main_module_code_in_process.py", app_args=[start_method])


# Test the basic usage of high-level `concurrent.futures` framework with its `ProcessPoolExecutor` (i.e., with default
# `multiprocessing` start method). This test will be more interesting if/when we can remove the explicit
# `multiprocessing.freeze_support` call in the entry-point script.
@pytest.mark.timeout(timeout=60)
def test_concurrent_features_process_pool_executor(pyi_builder):
    pyi_builder.test_source(
        """
        import multiprocessing
        import concurrent.futures

        def square(x):
            return x * x


        if __name__ == '__main__':
            multiprocessing.freeze_support()

            values = range(10)
            with concurrent.futures.ProcessPoolExecutor() as executor:
                result = list(executor.map(square, values))

            assert result == [x * x for x in values]
        """
    )
