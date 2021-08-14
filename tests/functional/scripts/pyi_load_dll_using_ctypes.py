#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os
import sys
from ctypes import CDLL

from pyi_get_datadir import get_data_dir

# Library name based on platform.
if sys.platform.startswith('win32'):
    name = 'ctypes_dylib.dll'
elif sys.platform.startswith("darwin"):
    name = 'ctypes_dylib.dylib'
else:
    name = 'ctypes_dylib.so'

# Test resolving dynamic libraries loaded in Python code at runtime by Python module 'ctypes'.
tct = CDLL(os.path.join(get_data_dir(), 'ctypes_dylib', name))
# The "dummy" function in ctypes_dylib returning value + 12.
assert tct.dummy(42) == (42 + 12)
