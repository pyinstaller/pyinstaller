# -*- mode: python -*-
a = Analysis([os.path.join(HOMEPATH, 'support', '_mountzlib.py'),
              os.path.join(HOMEPATH, 'support', 'useUnicode.py'),
              'test16.py'], pathex=['.'])

pyz = PYZ(a.pure)
exe = EXE( pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=os.path.join('dist', 'test16.exe'),
          debug=False,
          strip=False,
          upx=True,
          console=1 )

