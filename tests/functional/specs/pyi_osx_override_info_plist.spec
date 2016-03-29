# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


block_cipher = None
app_name = 'pyi_osx_override_info_plist'


a = Analysis(['../scripts/pyi_helloworld.py'],
             pathex=[],
             binaries=None,
             datas=None,
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
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name=app_name)
app = BUNDLE(coll,
             name=app_name + '.app',
             icon=None,
             bundle_identifier=None,
             # Override some values in generated 'Info.plist'.
             info_plist={
               'NSHighResolutionCapable': 'True',
               'LSUIElement': '1',
             })
