#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import ctypes, ctypes.util

# Make sure we are able to load the MSVCRXX.DLL resp. libc.so we are
# currently bound. This is some of a no-brainer since the resp. dll/so
# is collected anyway.
lib = ctypes.CDLL(ctypes.util.find_library('c'))
assert lib is not None
