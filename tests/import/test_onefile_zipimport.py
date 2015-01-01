#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from __future__ import print_function

# Test for zipimport - minimalistic, just import pgk_resource


import os
import sys

print(__name__, 'is running')
print('sys.path:', sys.path)
print('dir contents .exe:', os.listdir(os.path.dirname(sys.executable)))
print('-----------')
print('dir contents sys._MEIPASS:', os.listdir(sys._MEIPASS))

print('-----------')
print('now importing pkg_resources')
import pkg_resources
print("dir(pkg_resources)", dir(pkg_resources))
