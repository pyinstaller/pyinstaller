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

app_name = 'pyi_unbuffered_output'

a = Analysis([os.path.join(os.path.dirname(SPECPATH), 'scripts/pyi_unbuffered_output.py')])
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz,
          a.scripts,
          [('u', None, 'OPTION'), ],
          exclude_binaries=True,
          name=app_name,
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=True)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               upx_exclude=[],
               name=app_name)
