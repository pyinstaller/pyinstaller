#-----------------------------------------------------------------------------
# Copyright (c) 2015-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import sys

# Installing `osgeo` Conda packages requires to set `GDAL_DATA`

is_win = sys.platform.startswith('win')
if is_win:

    gdal_data = os.path.join(sys._MEIPASS, 'data', 'gdal')
    if not os.path.exists(gdal_data):

        gdal_data = os.path.join(sys._MEIPASS, 'Library', 'share', 'gdal')
        # last attempt, check if one of the required file is in the generic folder Library/data
        if not os.path.exists(os.path.join(gdal_data, 'gcs.csv')):
            gdal_data = os.path.join(sys._MEIPASS, 'Library', 'data')

else:
    gdal_data = os.path.join(sys._MEIPASS, 'share', 'gdal')

if os.path.exists(gdal_data):
    os.environ['GDAL_DATA'] = gdal_data
