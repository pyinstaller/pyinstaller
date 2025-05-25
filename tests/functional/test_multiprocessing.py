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
import subprocess

import pytest

from PyInstaller.compat import is_win, is_cygwin

if is_win:
    # On Windows, only spawn method is supported.
    START_METHODS = ['spawn']
elif is_cygwin:
    # Under Cygwin, forkserver does not seem to work even in unfrozen python.
    START_METHODS = ['spawn', 'fork']
else:
    # On POSIX systems (including macOS), all methods are supported.
    START_METHODS = ['spawn', 'fork', 'forkserver']


@pytest.mark.parametrize("start_method", START_METHODS)
def test_multiprocessing_process(pyi_builder, start_method):
    pyi_builder.test_script("pyi_multiprocessing_process.py", app_args=[start_method])


@pytest.mark.parametrize("start_method", START_METHODS)
def test_multiprocessing_queue(pyi_builder, start_method):
    pyi_builder.test_script("pyi_multiprocessing_queue.py", app_args=[start_method])


@pytest.mark.parametrize("start_method", START_METHODS)
def test_multiprocessing_pool(pyi_builder, start_method):
    pyi_builder.test_script("pyi_multiprocessing_pool.py", app_args=[start_method])


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
@pytest.mark.parametrize("start_method", START_METHODS)
def test_multiprocessing_process_start_in_threads(pyi_builder, start_method):
    pyi_builder.test_script("pyi_multiprocessing_process_start_in_threads.py", app_args=[start_method])


# Test that we can start a nested `multiprocessing.Process` from within a `multiprocessing.Process`. See #7494.
# Nested multi-processing is broken in Python 3.11.5 because SemLock.is_fork_ctx attribute (added in
# https://github.com/python/cpython/commit/34ef75d3ef559288900fad008f05b29155eb8b59) is not properly
# serialized/deserialized.
@pytest.mark.parametrize("start_method", START_METHODS)
@pytest.mark.xfail(sys.version_info[:3] == (3, 11, 5), reason="Python 3.11.5 broke nested multiprocessing.")
def test_multiprocessing_nested_process(pyi_builder, start_method):
    pyi_builder.test_script("pyi_multiprocessing_nested_process.py", app_args=[start_method])


# Test that we are able to retrieve the code object for `__main__` module in the sub-process.
# NOTE: in unfrozen version, this works only with `fork` start method. However, in current `multiprocessing` support,
# it should work with all start methods when frozen.
@pytest.mark.parametrize("start_method", START_METHODS)
def test_multiprocessing_main_module_code_in_process(pyi_builder, start_method):
    pyi_builder.test_script("pyi_multiprocessing_main_module_code_in_process.py", app_args=[start_method])


# Test the basic usage of high-level `concurrent.futures` framework with its `ProcessPoolExecutor` (i.e., with default
# `multiprocessing` start method). This test will be more interesting if/when we can remove the explicit
# `multiprocessing.freeze_support` call in the entry-point script.
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


# Test that application's top level directory (sys._MEIPASS) is properly inherited by multiprocessing child process.
@pytest.mark.parametrize("start_method", START_METHODS)
def test_multiprocessing_subprocess_environment(pyi_builder, start_method):
    pyi_builder.test_script("pyi_multiprocessing_subprocess_environment.py", app_args=[start_method])


# Test the inheritance of application's top level directory (sys._MEIPASS) into sub-processes that are manually spawned
# using `subprocess` module. If using the same executable (`sys.executable`), sys._MEIPASS should be inherited by the
# child process (in onefile mode, this means no unpacking). If it is a different executable, sys._MEIPASS should not be
# inherited (and a onefile child process should unpack itself).
def test_subprocess_environment_inheritance(pyi_builder_spec, tmp_path):
    # Build the spec. This will build a pair of identical onedir programs and a pair of identical onefile programs,
    # which we can then use to test all pertinent combinations. The `pyi_builder_spec` fixture attempts to run the built
    # executable, and for that part, we need to supply the executable name. Since no parameters are passed to the
    # executable, this is essentially no-op and serves just as a sanity check.
    pyi_builder_spec.test_spec('pyi_subprocess_environment_inheritance.spec', app_name='onedir_program_1')

    print("------- Running custom test. -------", file=sys.stderr)

    # "Manually" detertmine the executable paths, as `pyi_builder_spec._find_executables` cannot cope with custom names
    # that are used in the .spec file.
    dist_dir = tmp_path / 'dist'
    exe_suffix = ".exe" if is_win else ""

    onedir_program_1 = dist_dir / "onedir_program_1" / f"onedir_program_1{exe_suffix}"
    onedir_program_2 = dist_dir / "onedir_program_2" / f"onedir_program_2{exe_suffix}"
    onefile_program_1 = dist_dir / f"onefile_program_1{exe_suffix}"
    onefile_program_2 = dist_dir / f"onefile_program_2{exe_suffix}"

    assert onedir_program_1.is_file()
    assert onedir_program_2.is_file()
    assert onefile_program_1.is_file()
    assert onefile_program_1.is_file()

    # Test all relevant combinations; the programs in pairs are functionally identical, so we need to test only one
    # combination (for example, onedir_program_2 exists only so that onedir_program_1 can use it as a child, but the
    # two are otherwise identical).

    print("--- Test: onedir program spawns child via sys.executable...", file=sys.stderr)
    subprocess.check_call([onedir_program_1, 'parent', 'sys.executable'])

    print("--- Test: onefile program spawns child via sys.executable...", file=sys.stderr)
    subprocess.check_call([onefile_program_1, 'parent', 'sys.executable'])

    print("--- Test: onedir program spawns the other onedir program...", file=sys.stderr)
    subprocess.check_call([onedir_program_1, 'parent', onedir_program_2])

    print("--- Test: onedir program spawns onefile program...", file=sys.stderr)
    subprocess.check_call([onedir_program_1, 'parent', onefile_program_1])

    print("--- Test: onefile program spawns the other onefile program...", file=sys.stderr)
    subprocess.check_call([onefile_program_1, 'parent', onefile_program_2])

    print("--- Test: onefile program spawns onedir program...", file=sys.stderr)
    subprocess.check_call([onefile_program_1, 'parent', onedir_program_1])

    # Test the scenarios where we explicitly force independent instance of the same application.
    # NOTE: this applies only to onefile mode
    print("--- Test: onefile program spawns independent instance via sys.executable...", file=sys.stderr)
    subprocess.check_call([onefile_program_1, 'parent', 'sys.executable', '--force-independent'])
