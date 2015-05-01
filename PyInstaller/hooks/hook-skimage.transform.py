#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Hook tested with scikit-image (skimage) 0.9.3 on Mac OS 10.9 and Windows 7
# 64-bit
hiddenimports = ['skimage.draw.draw',
                 'skimage._shared.geometry',
                 'skimage._shared.interpolation',
                 'skimage.filter.rank.core_cy']
