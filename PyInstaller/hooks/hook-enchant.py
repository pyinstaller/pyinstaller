#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.compat import is_win
from PyInstaller.utils.hooks.hookutils import eval_script


if is_win:
    files = eval_script('enchant_datafiles_finder.py')
    datas = []  # data files in PyInstaller hook format
    for d in files:
        for f in d[1]:
            datas.append((f, d[0]))
