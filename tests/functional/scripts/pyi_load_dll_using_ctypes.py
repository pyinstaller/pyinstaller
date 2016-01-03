#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
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

# Test resolving dynamic libraries loaded in Python code at runtime
# by Python module 'ctypes'.
tct = CDLL(os.path.join(get_data_dir(), 'ctypes_dylib', name))
# The "dummy" function in ctypes_dylib returning value + 12.
assert tct.dummy(42) == (42 + 12)

