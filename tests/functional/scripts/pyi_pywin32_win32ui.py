#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Test importing some modules from pywin32 package.
# All modules from pywin32 depens on module pywintypes.
# This module should be also included.


import win32ui
from pywin.mfc.dialog import Dialog

d = Dialog(win32ui.IDD_SIMPLE_INPUT)
