#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# same test of test-ctypes-cdll-c.py, but built in one-file mode
import ctypes, ctypes.util


# Make sure we are able to load the MSVCRXX.DLL we are currently bound
# to through ctypes.
lib = ctypes.CDLL(ctypes.util.find_library('c'))
print(lib)
