#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


hiddenimports = [
    # win32com client and server util
    # modules could be hidden imports
    # of some modules using win32com.
    # Included for completeness.
    'win32com.client.util',
    'win32com.server.util',
]
