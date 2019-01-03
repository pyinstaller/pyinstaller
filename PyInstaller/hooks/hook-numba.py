#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# NumPy aware dynamic Python compiler using LLVM
# https://github.com/numba/numba
#
# Tested with:
# numba 0.26 (Anaconda 4.1.1, Windows), numba 0.28 (Linux)

excludedimports = ["IPython", "scipy"]
hiddenimports = ["llvmlite"]
