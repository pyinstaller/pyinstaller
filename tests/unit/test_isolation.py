#-----------------------------------------------------------------------------
# Copyright (c) 2021-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) or, at the user's discretion, the MIT License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception OR MIT)
#-----------------------------------------------------------------------------

import os
import logging

import pytest

from PyInstaller import isolated
from PyInstaller import compat
from PyInstaller.utils.tests import requires


def add_1(x):
    return x + 1


def fail():
    assert 0, "It's broken!"


def test_basic():
    assert isolated.call(add_1, 10) == 11
    assert isolated.call(add_1, x=4) == 5
    assert isolated.call(lambda: print("hello")) is None


def test_exception_handling():
    """
    Test the behaviour which an error is raised in the child process.
    """
    # Raising an error in a subprocess should propagate to a runtime error in the master process.
    with pytest.raises(RuntimeError) as ex_info:
        isolated.call(fail)
    # The exception should include the offending function's name and the child's traceback which itself includes the
    # breaking line of code and the exception type and message (in that order). Unfortunately, there seems to be a bug
    # in pytest's exception rewriting which makes the exception type and message unverifiable when ran under pytest.
    assert ex_info.match(r"""(?s) call to fail\(\) failed .* assert 0, "It's broken!".*""")
    # It should have removed the following line.
    assert "Traceback (most recent call last)" not in str(ex_info.value)


def test_multiple_calls():
    """
    Test running multiple functions in one process.
    """
    with isolated.Python() as child:
        assert child.call(add_1, 1) == 2
        assert child.call(add_1, 2) == 3
        assert child.call(add_1, 3) == 4


def test_builtins_access():
    """
    Ensure that generic builtins are accessible and that imports work.
    """
    def _use_builtins():
        """
        Test builtin functions, classes and constants are available.
        """
        assert sum([1, 2, 3]) == 6
        list(range(10))
        print("hello")
        Ellipsis
        ...
        NotImplemented

    def _use_imports():
        """
        Test that import-ing is possible.
        """
        import string
        string.digits

        import json
        return json.dumps({'a': 1, 'b': 2})

    with isolated.Python() as child:
        child.call(_use_builtins)
        child.call(_use_imports)


def test_context_wrapping():
    """
    Test the `with` mechanisms of IsolatedPython().

    We can land in some pretty horrible deadlocks if we try talking to a subprocess which either doesn't yet exist or
    has died. Make sure neither of these are possible.

    """
    self = isolated.Python()

    # Don't allow calling a function without using the context manager.
    with pytest.raises(RuntimeError, match="isolated.Python .* 'with' clause"):
        assert self.call(add_1, 1) == 2

    # Multiple enters/exits should work (although they're technically pointless, being equivalent to two
    # isolated.Python() instances).
    with self:
        assert self.call(add_1, 5.1) == 6.1
    with self:
        self.call(add_1, 2) == 3

    # The isolator should remain alive and functional after raising an error.
    with self:
        with pytest.raises(RuntimeError):
            self.call(add_1, "I should be a number")
        assert self.call(add_1, 2.5) == 3.5


def add_spam_to_environ():
    """
    Set an environment variable.
    """
    import os
    os.environ["SPAM"] = "More Spam"
    return "Done it!"


def get_spam_environ():
    import os
    return os.environ.get("SPAM")


def test_environment_propagation(monkeypatch):
    """
    Test that environment variables from the parent process are copied by the child but not the other way around.
    """
    # Clear the SPAM variable globally.
    monkeypatch.delenv("SPAM", raising=False)

    with isolated.Python() as child:
        # There should be no SPAM defined in the child.
        assert child.call(get_spam_environ) is None

        # Define SPAM in the child.
        child.call(add_spam_to_environ)
        # This should change the child environment...
        assert child.call(get_spam_environ) == "More Spam"
        # ... but not the parent.
        assert get_spam_environ() is None

    # Define SPAM globally.
    monkeypatch.setenv("SPAM", "More Spam")
    assert get_spam_environ() == "More Spam"
    # SPAM should be forwarded to new children.
    assert isolated.call(get_spam_environ) == "More Spam"


def test_decorator():
    """
    Test decorating a function with @wrap_with_isolation().
    """
    wrapped = isolated.decorate(add_spam_to_environ)
    assert wrapped.__doc__ == add_spam_to_environ.__doc__

    assert wrapped() == "Done it!"
    assert "SPAM" not in os.environ


@requires("psutil")
def test_pipe_leakage():
    """
    There is a finite number of open pipes/file handles/file descriptors allowed per process. Ensure that all
    opened handles eventually get closed to prevent such *leakages* causing crashes in very long processes (such as
    the rest of our test suite).
    """

    from psutil import Process
    parent = Process()

    # On Windows, the very first `subprocess.Popen()` seems to open two additional handles, which seem to remain open
    # for the duration of the python process. Therefore, if a subprocess is spawned before this test is ran (either as
    # a part of a preceding test, as a part of test collection, or even as a side effect of some 3rd party package
    # having been loaded), those two extra handles will already be part of the initially-opened handles. If not, they
    # will show up during this test and skew the results. Therefore, run a dummy subprocess here to normalize the
    # conditions, and ensure that the test can be ran on its own.
    if compat.is_win:
        import subprocess
        import sys
        proc = subprocess.Popen(
            [sys.executable, '--version'],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait()
        del proc

    # Get this platform's *count open handles* method.
    open_fds = parent.num_handles if compat.is_win else parent.num_fds
    old = open_fds()

    # Creating an isolated.Python() does nothing.
    child = isolated.Python()
    assert open_fds() == old

    # On POSIX systems, entering the context creates the child process and 4 handles for sending/receiving to/from it.
    # After creating the child process, we close the descriptors that were passed to the child, so the expected total
    # increase in the parent/main process is two file descriptors.
    #
    # On Windows, the overall setup is a bit more complicated. We create both pipes, spawn the child process, and close
    # end-points (handles) of the pipes that were passed to the child. Then, we open file descriptors on top of the
    # remaining two pipe handles, using `msvcrt.open_osfhandle`. These descriptors are then passed to `os.fdopen` to
    # obtain buffered python `file` object.
    #
    # Instead of monitoring file descriptors, we monitor file handles.
    #
    # Under python 3.12 and earlier, four handles are opened when both pipes are created. Additional two handles are
    # opened when the child process is spawned. Closing the two pipe end-points closes two handles. Opening file
    # descriptors on top of pipe handles (`msvcrt.open_osfhandle`) does not open additional handles, but opening
    # python file objects on top of those descriptors via `os.fdopen` does - one for each file object. This adds two
    # additional file handles, bringing us to the total of six.
    #
    # With python 3.13, the behavior has changed. Creating both pipes still opens four handles. However, spawning the
    # child process opens only one handle. Closing the two pipe end-points closes two handles. No additional handles
    # are created when opening file descriptors on top of pipe handles (`msvcrt.open_osfhandle`), nor when opening
    # python file objects on top of those (`os.fdopen`). So in this case, the total is three.
    if compat.is_win:
        EXPECTED_INCREASE_IN_FDS = 3 if compat.is_py313 else 6
    else:
        EXPECTED_INCREASE_IN_FDS = 2

    with child:
        assert open_fds() == old + EXPECTED_INCREASE_IN_FDS
    # Exiting must close them all immediately. No implicit closure by garbage collect.
    assert open_fds() == old

    # Do it again just to be sure that the context manager properly restarts.
    with child:
        assert open_fds() == old + EXPECTED_INCREASE_IN_FDS
    assert open_fds() == old


def is_isolated():
    """
    This is the recommended way of testing if you currently in an isolated process.
    """
    return globals().get("__isolated__", False)


def test_is_isolated():
    """
    Verify that the is_isolated() check returns true in isolation and false in this parent process.
    """
    assert is_isolated() is False
    assert isolated.call(is_isolated) is True
    assert is_isolated() is False


def test_default_args():
    """
    Verify that default arguments are properly passed to the isolated function call.
    """
    def isolated_function(arg1='default1', arg2='default2', arg3='default3'):
        return arg1, arg2, arg3

    # Sanity check
    assert isolated_function.__defaults__ == ('default1', 'default2', 'default3')
    assert isolated_function.__kwdefaults__ is None

    # Test by keeping the second argument at the default value
    expected = 'override1', 'default2', 'override3'
    with isolated.Python() as child:
        actual = child.call(isolated_function, arg1='override1', arg3='override3')
    assert actual == expected


def test_default_kwargs():
    """
    Verify that default keyword-only arguments are properly passed to the isolated function call.
    """
    def isolated_function(*args, kwarg1='default1', kwarg2='default2', kwarg3='default3'):
        return kwarg1, kwarg2, kwarg3

    # Sanity check
    assert isolated_function.__defaults__ is None
    assert isolated_function.__kwdefaults__ == {'kwarg1': 'default1', 'kwarg2': 'default2', 'kwarg3': 'default3'}

    # Test by keeping the second keyword-only argument at the default value
    expected = 'override1', 'default2', 'override3'
    with isolated.Python() as child:
        actual = child.call(isolated_function, kwarg1='override1', kwarg3='override3')
    assert actual == expected


@pytest.mark.parametrize("strict_mode", [True, False], ids=['strict', 'lax'])
def test_shutdown_timeout_dangling_threads(strict_mode, caplog):
    """
    Simulate the scenario from #7290, where the isolated sub-process ends up spawning a non-daemon thread, which
    prevents the sub-process from shutting down and in turn blocks the parent process on its _child.wait() call.

    This situation might arise when, as part of analysis, PyInstaller performs an isolated import of a module
    that spawns threads as part of executable statements that are ran on the first time the module is imported.
    """
    def isolated_function(*args):
        import threading
        import time

        # Simulate some long-running background task with periodic activity
        def background_task():
            while True:
                time.sleep(1)

        thread = threading.Thread(target=background_task, name="Test non-daemon thread", daemon=False)
        thread.start()

        return args

    expected = ('a', 'b', 'c', 1, 2, 3)

    if strict_mode:
        # In strict mode, we expect an error to be raised
        with pytest.raises(RuntimeError, match="Timed out while waiting for the child process to exit!"):
            with isolated.Python(strict_mode=strict_mode) as child:
                actual = child.call(isolated_function, *expected)
    else:
        # In lax mode, we expect a warning message
        with caplog.at_level(logging.WARNING):
            with isolated.Python(strict_mode=strict_mode) as child:
                actual = child.call(isolated_function, *expected)

            assert "Timed out while waiting for the child process to exit!" in caplog.text

        # The isolated function should finish and return its expected results, regardless of the shutdown timeout.
        assert actual == expected


def test_subprocess_crash():
    def crash(a):
        import os
        os.kill(os.getpid(), 9)

    with pytest.raises(
        isolated._parent.SubprocessDiedError, match=r"died calling crash\(\) with args=\(12,\) and kwargs=\{\}. .* -?9"
    ):
        isolated.call(crash, 12)


# Nested isolated subprocesses are not supported; attempts to use PyInstaller.isolated from within an isolated
# subprocess should end up reusing the already-existing isolated subprocess. This behavior allows various hook utility
# functions to be transparently used in the same isolated subprocess instead of having them potentially spawn their
# own subprocesses (each of those having to import package(s) again).
def test_nested_isolation():
    def isolated_function():
        from PyInstaller import isolated
        import os

        # Get this process ID of this (isolated process)
        pid = os.getpid()

        @isolated.decorate
        def isolated_subfunction():
            import os
            return os.getpid()

        other_pid = isolated_subfunction()
        return pid, other_pid

    # Test the isolated.call invocation
    pid, other_pid = isolated.call(isolated_function)
    assert pid == other_pid, f"Did not reuse the same isolated process: {pid} vs. {other_pid}"

    # Test the isolated.call invocation
    with isolated.Python() as subprocess:
        pid, other_pid = subprocess.call(isolated_function)
    assert pid == other_pid, f"Did not reuse the same isolated process: {pid} vs. {other_pid}"
