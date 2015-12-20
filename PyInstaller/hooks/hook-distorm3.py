#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import site
import os
from PyInstaller.compat import is_win
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files
if is_win:
   datas = [ ( os.path.join(site.getsitepackages()[1], 'distorm3\distorm3.dll'),
   #Not tested on Linux yet
