# -*- mode: python -*-

__testname__ = 'test-relative-import2'

a = Analysis([os.path.join(HOMEPATH,'support/_mountzlib.py'),
              __testname__ + '.py'],
             )
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          name = os.path.join('dist', __testname__, __testname__ +'.exe'),
          debug=False,
          strip=False,
          upx=False,
          console=1 )
