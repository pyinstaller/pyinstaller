#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os

import sys
from ctypes import CDLL

# Library name based on platform.
if sys.platform.startswith('win32'):
    name = 'ctypes_dylib.dll'
elif sys.platform.startswith("darwin"):
    name = 'ctypes_dylib.dylib'
else:
    name = 'ctypes_dylib.so'
exec_dir = os.path.dirname(sys.executable)

# onedir mode:
# tmpdir
# ├── ctypes_dylib.dll
# ├── ctypes_dylib.so
# ├── ctypes_dylib.dylib
# ├── build
# └── dist
#     └── appname
#         └── appname.exe
pth_onedir = os.path.join(exec_dir, '..', '..', 'data', 'load_dll_using_ctypes', name)
# onefile mode:
# tmpdir
# ├── ctypes_dylib.dll
# ├── ctypes_dylib.so
# ├── ctypes_dylib.dylib
# ├── build
# └── dist
#     └── appname.exe
pth_onefile = os.path.join(exec_dir, '..', 'data', 'load_dll_using_ctypes', name)
lib_filename = pth_onedir if os.path.exists(pth_onedir) else pth_onefile


def dummy(arg):
    """
    Test loading ctypes library and passing an argument to it.
    """
    tct = CDLL(lib_filename)
    return tct.dummy(arg)


# Test resolving dynamic libraries loaded in Python code at runtime
# by Python module 'ctypes'
assert dummy(42) == 42
