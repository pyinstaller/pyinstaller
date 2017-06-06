#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.compat import is_win
from PyInstaller.utils.hooks import collect_submodules

import sys

hiddenimports = collect_submodules('package')

if is_win:
  datas = [
    (sys.prefix+r'\tcl\tix8.4.3', r'/tcl/tix8.4.3'),
    (sys.prefix+r'\tcl\tix8.4.3\bitmaps', r'/tcl/tix8.4.3/bitmaps'),
    (sys.prefix+r'\tcl\tix8.4.3\pref', r'/tcl/tix8.4.3/pref')
  ]
