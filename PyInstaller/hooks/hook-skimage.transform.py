#-----------------------------------------------------------------------------
# Copyright (c) 2014-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
from PyInstaller.utils.hooks import collect_data_files

# Hook tested with scikit-image (skimage) 0.9.3 on Mac OS 10.9 and Windows 7
# 64-bit
hiddenimports = ['skimage.draw.draw',
                 'skimage._shared.geometry',
                 'skimage._shared.transform',
                 'skimage.filters.rank.core_cy']

datas = collect_data_files('skimage')
