#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys

def hook(mod):
    # Forbid imports in the port_v3 directory under Python 2
    # The code wouldn't import and would crash the build process.
    if sys.hexversion < 0x03000000:
        mod.__path__ = []
    return mod


