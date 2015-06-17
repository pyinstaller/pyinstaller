#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Test resolving dynamic libraries loaded in Python code at runtime
# by Python module 'ctypes'


import ctypeslib

assert ctypeslib.dummy(42) == 42
