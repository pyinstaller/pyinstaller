#-----------------------------------------------------------------------------
# Copyright (c) 2015-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.compat import is_win

import os, sys


# mpl_toolkits.basemap (tested with v.1.0.7) is shipped with auxiliary data,
# usually stored in mpl_toolkits\basemap\data and used to plot maps
datas = collect_data_files('mpl_toolkits.basemap')

# - conda-specific
if hasattr(sys, 'real_prefix'):  # check if in a virtual environment
    root_path = sys.real_prefix
else:
    root_path = sys.prefix

if is_win:
    tgt_basemap_data = os.path.join('Library', 'share', 'basemap')
    src_basemap_data = os.path.join(root_path, 'Library', 'share', 'basemap')

else:  # both linux and darwin
    tgt_basemap_data = os.path.join('share', 'basemap')
    src_basemap_data = os.path.join(root_path, 'share', 'basemap')

if os.path.exists(src_basemap_data):
    datas.append((src_basemap_data, tgt_basemap_data))
