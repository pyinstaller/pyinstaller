#-----------------------------------------------------------------------------
# Copyright (c) 2019-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Tested on Windows 10 1809 64bit with scikit-learn 0.22.1 and Python 3.7
hiddenimports = ['sklearn.neighbors.typedefs',
                 'sklearn.utils._cython_blas',
                 'sklearn.neighbors.quad_tree',
                 'sklearn.tree._utils']
