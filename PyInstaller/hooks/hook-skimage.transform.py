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
from PyInstaller.utils.hooks import collect_data_files

# Hook tested with scikit-image (skimage) 0.9.3 on Mac OS 10.9 and Windows 7
# 64-bit
hiddenimports = ['skimage.draw.draw',
                 'skimage._shared.geometry',
                 'skimage._shared.transform',
                 'skimage.filters.rank.core_cy']

datas = collect_data_files('skimage')
