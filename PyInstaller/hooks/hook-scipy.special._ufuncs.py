#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Module scipy.io._ufunc on some other C/C++ extensions.
# The hidden import is necessary for SciPy 0.13+.
# Thanks to dyadkin, see issue #826.
hiddenimports = ['scipy.special._ufuncs_cxx']
