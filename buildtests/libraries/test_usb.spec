# -*- mode: python -*-
a = Analysis(['test_usb.py'],
             pathex=['/home/zero/src/epl/EcoMultiStation/Driver/ExeBuilder/pyinstaller/buildtests/libraries'],
             hiddenimports=[],
             hookspath=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build/pyi.linux2/test_usb', 'test_usb'),
          debug=True,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name=os.path.join('dist', 'test_usb'))
