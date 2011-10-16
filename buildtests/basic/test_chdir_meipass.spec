# -*- mode: python -*-

__testname__ = 'test_chdir_meipass'

a = Analysis([os.path.join(HOMEPATH, 'support', '_mountzlib.py'),
              os.path.join(CONFIGDIR, 'support', 'useUnicode.py'),
              __testname__ + '.py'], pathex=['.'])

pyz = PYZ(a.pure)
exe = EXE( pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=os.path.join('dist', __testname__, __testname__ + '.exe'),
          debug=False,
          strip=False,
          upx=True,
          console=1 )

