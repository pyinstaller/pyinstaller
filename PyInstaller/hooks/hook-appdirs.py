#-----------------------------------------------------------------------------
# Copyright (c) 2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Import hook for appdirs.

On Windows, appdirs tries 2 different methods to get well-known directories
from the system: First with win32com, then with ctypes. Excluding win32com here
avoids including all the win32com related DLLs in programs that don't include
them otherwise.
"""

excludedimports = ['win32com']
