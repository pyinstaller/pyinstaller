#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os

from PyInstaller.compat import is_win, is_darwin
from PyInstaller.utils.hooks.hookutils import exec_statement, collect_data_files, eval_script


if is_win:
    files = eval_script('enchant_datafiles_finder.py')
    datas = []  # data files in PyInstaller hook format
    for d in files:
        for f in d[1]:
            datas.append((f, d[0]))
elif is_darwin:
    # Collecting dictionaries only works when pyenchant is installed via pip since the dictionaries installed via pip
    # are stored next to the enchant library
    binaries = []
    files = exec_statement("""
from enchant._enchant import e
print(e._name)""").strip().split()
    for f in files:  # Put the enchant library in lib/ so the enchant plugins can find it
        binaries.append((f, 'lib'))
    files = exec_statement("""
from enchant import Broker
for provider in Broker().describe():
    print(provider.file)""").strip().split()
    for f in files:  # Put enchant plugins in lib/enchant/ so the enchant library can find them
        binaries.append((f, os.path.join('lib', 'enchant')))

    datas = []
    files = collect_data_files('enchant')  # Only works if pyenchant is installed via pip
    for file in files:
        if 'share' in file[0] and not file[0].endswith('.zip') and 'man' not in file[0]:
            datas.append((file[0], os.sep.join(file[1].split(os.sep)[1:])))
