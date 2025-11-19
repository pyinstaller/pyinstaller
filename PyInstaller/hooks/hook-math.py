#-----------------------------------------------------------------------------
# Copyright (c) 2025, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.compat import is_py315

hiddenimports = []

# Starting with python 3.15.0a2, the stdlib `math` extension depends on `_math_integer` extension (PEP-791).
# See: https://github.com/python/cpython/commit/dcf3cc5796693ba3c3d1ddb8659849635e4fa373
if is_py315:
    hiddenimports = ['_math_integer']
