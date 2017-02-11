#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.compat import is_win
import sys

if is_win:
  datas = [
    (sys.prefix+'\DLLs\tix84*.dll', 'dlls'),
    (sys.prefix+'\tcl\tix8.4.3', '/tcl/tix8.4.3'),
    (sys.prefix+'\tcl\tix8.4.3\bitmaps', '/tcl/tix8.4.3/bitmaps'),
    (sys.prefix+'\tcl\tix8.4.3\pref', '/tcl/tix8.4.3/pref')
  ]
