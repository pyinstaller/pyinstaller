#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys

def pre_find_module_path(hook_api):
    # Forbid imports in the port_v2 directory under Python 3
    # The code wouldn't import and would crash the build process.
    if sys.hexversion >= 0x03000000:
        hook_api.search_dirs = []


