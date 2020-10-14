#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller import compat


def test_exec_command_subprocess_wrong_encoding_stdout_salvageable():
    # Ensure that even if the stdout of the executed command contains
    # invalid characters (mismatched encoding or just garbage), the
    # rest of the output is still salvageable and can be parsed.
    # `exec_python()` is used for running the progam, so we can use a
    # small Python script.
    prog = (
        "import sys; "
        "sys.stdout.buffer.write(b'dfadfadf\\xa0:::::'); "
        "sys.stdout.buffer.write(b'MessageOfInterest')"
    )

    out = compat.exec_python('-c', prog)
    assert 'MessageOfInterest' in out
