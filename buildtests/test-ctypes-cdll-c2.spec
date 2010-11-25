# -*- mode: python -*-

__testname__ = 'test-ctypes-cdll-c2'

a = Analysis([os.path.join(HOMEPATH,'support', '_mountzlib.py'),
              os.path.join(HOMEPATH,'support', 'useUnicode.py'),
              __testname__ + '.py'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.binaries,
          a.zipfiles,
          a.scripts,
          name=os.path.join('dist', __testname__ + '.exe'),
          debug=True,
          strip=False,
          upx=False,
          console=1 )
