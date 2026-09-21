#-----------------------------------------------------------------------------
# Copyright (c) 2005-2026, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""Windows EXE name suffix must be detected case-insensitively (see #9527 for .SPEC)."""

import pytest

from PyInstaller.building.api import _ensure_windows_exe_suffix


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("myapp", "myapp.exe"),
        ("myapp.exe", "myapp.exe"),
        ("myapp.EXE", "myapp.EXE"),
        ("myapp.Exe", "myapp.Exe"),
        (r"C:\dist\myapp.EXE", r"C:\dist\myapp.EXE"),
    ],
)
def test_windows_exe_suffix_casefold(name, expected):
    assert _ensure_windows_exe_suffix(name) == expected
