# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['../scripts/osx console option.py'])
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='osx console option',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='osx console option')
app = BUNDLE(coll,
             name='osx console option.app',
             icon=None,
             bundle_identifier=None,
             osx_app_console=True)
