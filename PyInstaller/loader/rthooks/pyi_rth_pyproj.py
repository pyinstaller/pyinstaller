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

import os
import sys

# Installing `pyproj` Conda packages requires to set `PROJ_LIB`

is_win = sys.platform.startswith('win')
if is_win:

    proj_data = os.path.join(sys._MEIPASS, 'Library', 'share', 'proj')

else:
    proj_data = os.path.join(sys._MEIPASS, 'share', 'proj')

if os.path.exists(proj_data):
    os.environ['PROJ_LIB'] = proj_data
