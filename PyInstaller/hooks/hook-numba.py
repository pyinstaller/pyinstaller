#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
#
# NumPy aware dynamic Python compiler using LLVM
# https://github.com/numba/numba
#
# Tested with:
# numba 0.26 (Anaconda 4.1.1, Windows), numba 0.28 (Linux)

excludedimports = ["IPython", "scipy"]
hiddenimports = ["llvmlite"]
