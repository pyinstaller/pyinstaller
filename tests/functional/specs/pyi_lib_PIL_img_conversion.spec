# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import sys

block_cipher = None
app_name = 'pyi_lib_PIL_img_conversion'
datas = [('../data/PIL_images', '.')]


a = Analysis(['../scripts/' + app_name + '.py'],
             pathex=[],
             binaries=None,
             datas=datas,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=None,
             excludes=None,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name=app_name,
          debug=True,
          strip=None,
          upx=False,
          # Use console mode or else on Windows the VS() messageboxes will stall pytest.
          console=True)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=False,
               name=app_name)
