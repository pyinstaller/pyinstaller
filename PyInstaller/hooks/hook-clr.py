#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Python.net requires Python.Runtime.dll which isn't found by PyInstaller.
"""


import ctypes.util
from PyInstaller.compat import is_win


# Python.net is available only for Windows.
if is_win:
    datas = [(ctypes.util.find_library('Python.Runtime'), '')]
