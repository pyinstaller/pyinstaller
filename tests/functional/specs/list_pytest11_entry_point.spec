# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from pathlib import Path
from PyInstaller.utils.hooks import collect_entry_point

app_name = 'list_pytest11_entry_point'

datas, hidden = collect_entry_point("pytest11")

a = Analysis([str(Path(SPECPATH).parent / 'scripts' / 'list_pytest11_entry_point.py')],
             datas=datas,
             hiddenimports=hidden)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz,
          a.scripts,
          [('u', None, 'OPTION'), ],
          exclude_binaries=True,
          name=app_name,
          debug=False,
          console=True)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               name=app_name)
