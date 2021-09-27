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

from PyInstaller.depend.bindepend import _library_matcher


def test_library_matcher():
    """
    Test that _library_matcher() is tolerant to version numbers both before and after the .so suffix but does not
    allow runaway glob patterns to match anything else.
    """
    m = _library_matcher("libc")
    assert m("libc.so")
    assert m("libc.dylib")
    assert m("libc.so.1")
    assert not m("libcrypt.so")

    m = _library_matcher("libpng")
    assert m("libpng16.so.16")
