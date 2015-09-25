#-----------------------------------------------------------------------------
# Copyright (c) 2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# ********************************************
# hook-u1db.py - Pyinstaller hook for u1db 
# ********************************************
from PyInstaller.hooks.hookutils import collect_data_files

datas = collect_data_files('u1db')
