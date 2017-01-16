#-----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


hiddenimports = [
    # win32com client and server util
    # modules could be hidden imports
    # of some modules using win32com.
    # Included for completeness.
    'win32com.client.util',
    'win32com.server.util',
]
