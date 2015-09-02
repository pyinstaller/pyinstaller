#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Library imports
# ---------------
import os
import sys
from ctypes import CDLL

# Local imports
# -------------
from pyi_get_datadir import get_data_dir

# Library name based on platform.
if sys.platform.startswith('win32'):
    name = 'ctypes_dylib.dll'
elif sys.platform.startswith("darwin"):
    name = 'ctypes_dylib.dylib'
else:
    name = 'ctypes_dylib.so'

def dummy(arg):
    """
    Test loading ctypes library and passing an argument to it.
    """
    tct = CDLL(os.path.join(get_data_dir(), 'load_dll_using_ctypes', name))
    return tct.dummy(arg)

# Test resolving dynamic libraries loaded in Python code at runtime
# by Python module 'ctypes'
assert dummy(42) == 42

