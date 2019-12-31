# -----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

# This module is not a "fake module" in the classical sense,
# but a real module that can be imported. It acts as an RPC
# interface for the functions of the bootloader.

"""
This module connects to the bootloader to send messages to the splash screen.

It is intended to act as a RPC interface for the functions provided by the
bootloader, such as displaying text or closing. This makes the users python
program independent of how the communication with the bootloader is
implemented, since a consistent API is provided.

To connect to the bootloader, it connects to a named pipe whose name is passed
through the environment variable '_PYIBoot_SPLASH'. The bootloader creates a
**unidirectional** pipe and keeps the read end so that it can receive messages.
Since the os-module, which is needed to request the environment variable,
is not available at boot time, the module does not establish the connection
until initialization.

The protocol by which the Python interpreter communicates with the bootloader
is implemented in this module, the protocol is described in the
:py:func:`pyi_splash._write_to_pipe` function.

This module does not support reloads while the splash screen is displayed, i.e.
it cannot be reloaded (such as by importlib.reload), because the splash
screen closes automatically when the connection to this instance of the
module is lost.
"""

__all__ = ['update_text', 'close', 'is_alive']

import atexit
import os
import struct
import sys
import logging

# Utility parameters/constants
is_win = sys.platform.startswith("win")
logger = logging.getLogger(__name__)
# First byte of the message must be the type of the event,
# followed by extra data. These event types are defined in the bootloader.
MSG_FINISH_TYPE = b'c'
MSG_UPDATE_TYPE = b'u'

# Module internal variables
_initialized = False
_pipe_write_file = None

# We expect a splash screen from the bootloader, but if _SPLASH
# is not set, the module cannot connect to it.
try:
    _pipe_name = os.environ['_PYIBoot_SPLASH']
    del os.environ['_PYIBoot_SPLASH']
except KeyError as _err:
    _pipe_name = None
    logger.warning("The environment does not allow connecting to the "
                   "splash screen. Are the splash resources attached "
                   "to the bootloader?", exc_info=_err)


def _initialize():
    """Initialize this module.

    Connect to the IPC server of the bootloader and open the pipe as
    a writeable file object. The output to the pipe file should be
    unbuffered, because the commands should be sent to the
    bootloader/IPC server as soon as writing to the file.
    """
    global _pipe_write_file, _initialized

    if is_win:
        import msvcrt
        import _winapi as winapi

        try:
            _write_handle = winapi.CreateFile(
                _pipe_name,            # file_name
                winapi.GENERIC_WRITE,  # desired_access
                0,                     # share_mode
                winapi.NULL,           # security_attributes
                winapi.OPEN_EXISTING,  # creation_disposition
                0,                     # flags_and_attributes
                winapi.NULL)           # template_file
            # create C runtime file descriptor
            _write_fd = msvcrt.open_osfhandle(_write_handle, os.O_WRONLY)

            # Open the file descriptor like a 'normal' file.
            _pipe_write_file = open(_write_fd,
                                    mode='wb',
                                    buffering=0,
                                    closefd=True)

            # The module is only initialized when nothing went wrong.
            _initialized = True
            logger.info("A connection to the splash screen was "
                        "successfully established.")
        except (OSError, IOError) as _err:
            raise ConnectionError("Unable to connect to the outbound"
                                  " pipe %s" % _pipe_name) from _err


# Initialize the connection upon importing this module.
# This will establish a connection to the bootloader's IPC
# server relatively quickly, so that any timeouts are avoided.
if _pipe_name:
    _initialize()


def _check_connection(func):
    """Utility decorator for checking whether the function should be executed.

    The wrapped function may raise a ConnectionError if the module was not
    initialized correctly.
    """

    def wrapper(*args, **kwargs):
        """Executes the wrapped function if the environment allows it.

        That is, if the connection to the bootloader has not been closed
        and the module is initialized.

        :raises ConnectionError: if the module was not initialized correctly
        """
        if _initialized and _pipe_write_file is None:
            logger.info("The module has been disabled, so the use of "
                        "the splash screen is no longer supported.")
            return  # The pipe has closed, so the interaction with this module
        elif not _initialized:
            raise ConnectionError("The connection is not initialized. "
                                  "Did this module failed to load?")

        return func(*args, **kwargs)

    try:
        # If functools is included, a 'nice' wrapper can be used
        from functools import update_wrapper
        return update_wrapper(wrapper, func)
    except ImportError:
        return wrapper


def _write_to_pipe(_type, _msg=b""):
    """
    Write data to the pipe.

    The bootloader will receive and process the data. Communication through
    the pipe is described with the following binary protocol:
        ipc_message[0]   := event type
        ipc_message[1:5] := custom event data length
        ipc_message[>5]  := custom event data
    (assuming ipc_message is a bytearray-like object)

    :param char _type: event type
    :param char* _msg: custom event data
    :raises ValueError or IOError: If the OS fails to write to the pipe
    """
    # Create message according to the protocol in native mode (@). The message
    # head has the format of:
    #
    #   typedef struct _ipc_message_head {
    #       char event_type;
    #       int text_length;
    #   } IPC_MESSAGE_HEAD;
    #
    # followed by the text
    msg_buf = struct.pack("c I %ds" % len(_msg),
                          _type,
                          len(_msg),
                          _msg)

    # Write to pipe file
    _pipe_write_file.write(msg_buf)


@atexit.register
def _close_pipe():
    """Close the pipe

    This function calls itself when the program is terminating via
    the atexit module, because the opened pipe must be closed.

    Windows closes a pipe automatically if both handles are closed, Linux
    on the other hand does not close the pipe automatically, i.e. it should
    be closed at the end of the program in any case.
    """
    global _pipe_write_file

    # No need to try it at all
    if _pipe_write_file is None:
        return

    try:
        _pipe_write_file.close()
    except (OSError, ValueError, IOError):
        # Ignore those error, since the OS mostly takes care of the unused or
        # invalid handle. Also, the handle in this module is set to None
        # afterwards, which renders this module unusable.
        pass
    finally:
        # Reset the handle
        _pipe_write_file = None


def is_alive():
    """Indicates whether the module can be used.

    Returns False if the module is either not initialized or was disabled
    by closing the splash screen. Otherwise, the module should be usable.
    """
    return _initialized and _pipe_write_file is not None


@_check_connection
def close():
    """Closes the splash screen window.

    This will close the splash screen and renders this module unusable.
    After this function is called, no connection can be opened to the splash
    screen again and all functions of this module become unusable.

    :raises ConnectionError: if the function is unable to send the close
                              message to the splash screen.
    """
    try:
        _write_to_pipe(MSG_FINISH_TYPE)
    except (ValueError, IOError):
        raise ConnectionError("Unable to write to the pipe")
    finally:
        # Close the pipe, no matter what happened
        _close_pipe()


@_check_connection
def update_text(msg):
    """Updates the text on the splash screen window.

    :param str msg: the text to be displayed.
    :raises ConnectionError: If the OS fails to write to the pipe
    """
    if not isinstance(msg, str):
        raise TypeError(
            "argument 'msg' must be str, not %s" % type(msg).__name__)

    try:
        _write_to_pipe(MSG_UPDATE_TYPE, msg.encode('utf-8'))
    except (ValueError, IOError):
        raise ConnectionError("Unable to write to the pipe")
