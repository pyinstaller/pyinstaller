#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#By Starwarsfan2099
from PyInstaller.compat import is_win, is_darwin
from PyInstaller.utils.hooks import get_package_paths

datas = [ ("C:\python27\Lib\site-packages\distorm3\distorm3.dll", ''), ]
if is_win:
    datas = [ ("C:\python27\Lib\site-packages\distorm3\distorm3.dll", ''), ]
else:
    raise ValueError('This distorm3 hook only works on Windows!')
