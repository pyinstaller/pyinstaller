#-----------------------------------------------------------------------------
# Copyright (c) 2015-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.utils.hooks import (collect_data_files)


# mpl_toolkits.basemap (tested with v.1.0.7) is shipped with auxiliary data,
# usually stored in mpl_toolkits\basemap\data and used to plot maps
datas = collect_data_files('mpl_toolkits.basemap')
