# -*- coding: utf-8 ; mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# spec-file containing some utf-8 umlauts
# äöu Čapek
"äöü Čapek"

app_name = "spec-with-utf8"

a = Analysis(['../scripts/pyi_helloworld.py'])
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name=app_name,
          debug=False, # the test is this .sepc-file
          console=True)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               name=app_name)
