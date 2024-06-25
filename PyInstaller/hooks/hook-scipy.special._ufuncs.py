#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import is_module_satisfies

# Module scipy.io._ufunc depends on some other C/C++ extensions. The hidden import is necessary for SciPy 0.13+.
# Thanks to dyadkin; see issue #826.
hiddenimports = ['scipy.special._ufuncs_cxx']

# SciPy 1.13.0 cythonized cdflib; this introduced new `scipy.special._cdflib` extension that is imported from the
# `scipy.special._ufuncs` extension, and thus we need a hidden import here.
if is_module_satisfies('scipy >= 1.13.0'):
    hiddenimports += ['scipy.special._cdflib']

# SciPy 1.14.0 introduced `scipy.special._special_ufuncs`, which is imported from `scipy.special._ufuncs` extension.
if is_module_satisfies('scipy >= 1.14.0'):
    hiddenimports += ['scipy.special._special_ufuncs']
