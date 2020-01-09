#-----------------------------------------------------------------------------
# Copyright (c) 2015-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.compat import is_win, base_prefix

import os, sys


# mpl_toolkits.basemap (tested with v.1.0.7) is shipped with auxiliary data,
# usually stored in mpl_toolkits\basemap\data and used to plot maps
datas = collect_data_files('mpl_toolkits.basemap', subdir='data')

# check if the data has been effectively found
if len(datas) == 0:
    
    # - conda-specific

    if is_win:
        tgt_basemap_data = os.path.join('Library', 'share', 'basemap')
        src_basemap_data = os.path.join(base_prefix, 'Library', 'share', 'basemap')

    else:  # both linux and darwin
        tgt_basemap_data = os.path.join('share', 'basemap')
        src_basemap_data = os.path.join(base_prefix, 'share', 'basemap')

    if os.path.exists(src_basemap_data):
        datas.append((src_basemap_data, tgt_basemap_data))
