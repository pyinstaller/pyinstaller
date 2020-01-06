#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


import sys

def pre_find_module_path(hook_api):
    # Forbid imports in the port_v3 directory under Python 2
    # The code wouldn't import and would crash the build process.
    if sys.hexversion < 0x03000000:
        hook_api.search_dirs = []
