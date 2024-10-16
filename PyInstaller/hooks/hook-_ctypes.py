#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller import compat

# During python 3.14 development cycle, ctypes struct/union layout logic has been moved from `_ctypes` extension into
# Python, i.e., `ctypes._layout` module: https://github.com/python/cpython/pull/123352
# Since this module is referenced only from the `_ctypes` extension, it needs to be added to hidden imports, at least on
# Windows and macOS.
if compat.is_py314:
    hiddenimports = ['ctypes._layout']
