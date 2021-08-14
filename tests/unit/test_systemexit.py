#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
In `#4592 <https://github.com/pyinstaller/pyinstaller/pull/4592>`_, the bootloader was modified to allow the execution
traceback to be shown in Windowed mode. Unfortunately, this modification caused the recurrence of a bug raised in #1869.
"""

import pytest


@pytest.mark.parametrize(
    'src,retcode',
    [
        # Code to run, retcode
        ('raise SystemExit', 0),
        ('import sys; sys.exit()', 0),
        ('raise SystemExit(1)', 1),
        ('import sys; sys.exit(2)', 2),
        ('raise SystemExit("Message to get printed to the console.")', 1),
        ('raise Exception("Unhandled exception.")', 1)  # See issue #5480
    ]
)
def test_systemexit_is_handled_correctly(src, retcode, pyi_builder):
    pyi_builder.test_source(src, retcode=retcode)
