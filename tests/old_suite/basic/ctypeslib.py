#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import sys
from ctypes import CDLL


if hasattr(sys, 'frozen'):
    lib_path = os.path.join(os.path.dirname(sys.executable), '..', 'ctypes')
else:
    lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ctypes')


def dummy(arg):
    """
    Test loading ctypes library and passing an argument to it.
    """
    if sys.platform.startswith('win32'):
        pth = os.path.join(lib_path, 'testctypes-win.dll')
    elif sys.platform.startswith("darwin"):
        pth = os.path.join(lib_path, 'testctypes.dylib')
    else:
        pth = os.path.join(lib_path, 'testctypes.so')
    tct = CDLL(pth)
    return tct.dummy(arg)
