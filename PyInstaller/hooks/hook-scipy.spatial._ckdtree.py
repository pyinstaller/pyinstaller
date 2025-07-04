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

from PyInstaller.utils.hooks import is_module_satisfies

# As of SciPy 1.16.0, `scipy.spatial._ckdtree` extension started to depend on newly-introduced `scipy._cyutility`.
if is_module_satisfies('scipy >= 1.16.0'):
    hiddenimports = ['scipy._cyutility']
