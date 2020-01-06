#-----------------------------------------------------------------------------
# Copyright (c) 2014-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Tested on Windows 7 64bit with scikit-learn 0.17 and Python 2.7
hiddenimports = ['sklearn.utils.sparsetools._graph_validation',
                 'sklearn.utils.sparsetools._graph_tools',
                 'sklearn.utils.lgamma',
                 'sklearn.utils.weight_vector']
