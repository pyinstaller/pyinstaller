# -----------------------------------------------------------------------------
# Copyright (c) 2021-2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

import os
from pathlib import Path
from marshal import loads, dumps
from base64 import b64encode, b64decode
import functools

from PyInstaller.compat import __wrap_python

if os.name == "nt":
    from msvcrt import get_osfhandle, open_osfhandle

    def open(osf_handle, mode):
        # Convert system file handles to file descriptors before opening them.
        return os.fdopen(open_osfhandle(osf_handle, 0), mode)

    def close(osf_handle):
        # Likewise when closing.
        return os.close(open_osfhandle(osf_handle, 0))

else:
    close = os.close

CHILD_PY = Path(__file__).with_name("_child.py")


def pipe():
    """
    Create a one-way pipe for sending data to child processes.

    Returns:
        A read/write pair of file descriptors (which are just integers) on posix or system file handle on Windows.

    The pipe may be used either by this process or subprocesses of this process but not globally.

    """
    read, write = os.pipe()
    # The default behaviour of pipes is that they are process specific. i.e. they can only be used for this process to
    # talk to itself. Setting these means that child processes may also use these pipes.
    os.set_inheritable(read, True)
    os.set_inheritable(write, True)

    # On Windows, file descriptors are not shareable. They need to be converted to system file handles here then
    # converted back with open_osfhandle() by the child.
    if os.name == "nt":
        read, write = get_osfhandle(read), get_osfhandle(write)

    return read, write


def child(read_from_parent: int, write_to_parent: int):
    """
    Spawn a Python subprocess sending it the two file descriptors it needs to talk back to this parent process.
    """
    from subprocess import Popen

    # Run the _child.py script directly passing it the two file descriptors it needs to talk back to the parent.
    cmd, options = __wrap_python(
        [str(CHILD_PY), str(read_from_parent), str(write_to_parent)],
        # Explicitly disabling close_fds is a requirement for making file descriptors inheritable by child processes.
        dict(close_fds=False, env=_subprocess_env()),
    )
    # I'm intentionally leaving stdout and stderr alone so that print() can still be used for emergency debugging and
    # unhandled errors in the child are still visible.
    return Popen(cmd, **options)


def _subprocess_env():
    """
    Define the environment variables to be readable in a child process.
    """
    from PyInstaller.config import CONF
    python_path = CONF["pathex"]
    if "PYTHONPATH" in os.environ:
        python_path = python_path + [os.environ["PYTHONPATH"]]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(python_path)
    return env


class Python:
    """
    Start and connect to a separate Python subprocess.

    This is the lowest level of public API provided by this module. The advantage of using this class directly is
    that it allows multiple functions to be evaluated in a single subprocess, making it faster than multiple calls to
    :func:`call`.

    Examples:
        To call some predefined functions ``x = foo()``, ``y = bar("numpy")`` and ``z = bazz(some_flag=True)`` all using
        the same isolated subprocess use::

            with isolated.Python() as child:
                x = child.call(foo)
                y = child.call(bar, "numpy")
                z = child.call(bazz, some_flag=True)

    """
    def __init__(self):
        self._child = None

    def __enter__(self):
        # We need two pipes. One for the child to send data to the parent.
        self._read_from_child, self._write_to_parent = pipe()
        # And one for the parent to send data to the child.
        self._read_from_parent, self._write_to_child = pipe()

        # Spawn a Python subprocess sending it the two file descriptors it needs to talk back to this parent process.
        self._child = child(self._read_from_parent, self._write_to_parent)

        # Open file handles to talk to the child.
        self._write_handle = open(self._write_to_child, "wb")
        self._read_handle = open(self._read_from_child, "rb")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Send the signal (a blank line) to the child to tell it that it's time to stop.
        self._write_handle.write(b"\n")
        self._write_handle.flush()
        self._child.wait()

        # Then close all the pipes and handles. These steps were determined empirically to appease the corresponding
        # test: tests/unit/test_isolation.py::test_pipe_leakage
        # I don't really understand why they must be this way.
        close(self._read_from_parent)
        close(self._write_to_parent)
        self._write_handle.close()
        self._read_handle.close()
        del self._read_handle, self._write_handle
        self._child = None

    def call(self, function, *args, **kwargs):
        """
        Call a function in the child Python. Retrieve its return value. Usage of this method is identical to that
        of the :func:`call` function.
        """
        if self._child is None:
            raise RuntimeError("An isolated.Python object must be used in a 'with' clause.")

        # Send 5 lines to the child process: The function's code attribute, its default args and kwargs, and its actual
        # args and kwargs, all serialised.
        self._write_handle.writelines([
            b64encode(dumps(function.__code__)), b"\n",
            b64encode(dumps(function.__defaults__)), b"\n",
            b64encode(dumps(function.__kwdefaults__)), b"\n",
            b64encode(dumps(args)), b"\n",
            b64encode(dumps(kwargs)), b"\n",
        ])  # yapf: disable

        # Flushing is very important. Without it, the data is not sent but forever sits in a buffer so that the child is
        # forever waiting for its data and the parent in turn is forever waiting for the child's response.
        self._write_handle.flush()

        # Read a single line of output back from the child. This contains if the function worked and either its return
        # value or a traceback. This will block indefinitely until it receives a '\n' byte.
        ok, output = loads(b64decode(self._read_handle.readline()))

        # If all went well, then ``output`` is the return value.
        if ok:
            return output

        # Otherwise an error happened and ``output`` is a string-ified stacktrace. Raise an error appending the
        # stacktrace. Having the output in this order gives a nice fluent transition from parent to child in the stack
        # trace.
        raise RuntimeError(f"Child process call to {function.__name__}() failed with:\n" + output)


def call(function, *args, **kwargs):
    r"""
    Call a function with arguments in a separate child Python. Retrieve its return value.

    Args:
        function:
            The function to send and invoke.
        *args:
        **kwargs:
            Positional and keyword arguments to send to the function. These must be simple builtin types - not custom
            classes.
    Returns:
        The return value of the function. Again, these must be basic types serialisable by :func:`marshal.dumps`.
    Raises:
        RuntimeError:
            Any exception which happens inside an isolated process is caught and reraised in the parent process.

    To use, define a function which returns the information you're looking for. Any imports it requires must happen in
    the body of the function. For example, to safely check the output of ``matplotlib.get_data_path()`` use::

        # Define a function to be ran in isolation.
        def get_matplotlib_data_path():
            import matplotlib
            return matplotlib.get_data_path()

        # Call it with isolated.call().
        get_matplotlib_data_path = isolated.call(matplotlib_data_path)

    For single use functions taking no arguments like the above you can abuse the decorator syntax slightly to define
    and execute a function in one go. ::

        >>> @isolated.call
        ... def matplotlib_data_dir():
        ...     import matplotlib
        ...     return matplotlib.get_data_path()
        >>> matplotlib_data_dir
        '/home/brenainn/.pyenv/versions/3.9.6/lib/python3.9/site-packages/matplotlib/mpl-data'

    Functions may take positional and keyword arguments and return most generic Python data types. ::

        >>> def echo_parameters(*args, **kwargs):
        ...     return args, kwargs
        >>> isolated.call(echo_parameters, 1, 2, 3)
        (1, 2, 3), {}
        >>> isolated.call(echo_parameters, foo=["bar"])
        (), {'foo': ['bar']}

    Notes:
        To make a function behave differently if it's isolated, check for the ``__isolated__`` global. ::

            if globals().get("__isolated__", False):
                # We're inside a child process.
                ...
            else:
                # This is the master process.
                ...

    """
    with Python() as isolated:
        return isolated.call(function, *args, **kwargs)


def decorate(function):
    """
    Decorate a function so that it is always called in an isolated subprocess.

    Examples:

        To use, write a function then prepend ``@isolated.decorate``. ::

            @isolated.decorate
            def add_1(x):
                '''Add 1 to ``x``, displaying the current process ID.'''
                import os
                print(f"Process {os.getpid()}: Adding 1 to {x}.")
                return x + 1

        The resultant ``add_1()`` function can now be called as you would a
        normal function and it'll automatically use a subprocess.

            >>> add_1(4)
            Process 4920: Adding 1 to 4.
            5
            >>> add_1(13.2)
            Process 4928: Adding 1 to 13.2.
            14.2

    """
    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        return call(function, *args, **kwargs)

    return wrapped
