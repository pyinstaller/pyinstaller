# -*- mode: python -*-
a = Analysis([os.path.join(HOMEPATH,'support/_mountzlib.py'),
              os.path.join(HOMEPATH,'support/useUnicode.py'), 
              'test-nestedlaunch1.py'],
             pathex=[''])
pyz = PYZ(a.pure)
exe = EXE( pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          name=os.path.join('dist', 'test-nestedlaunch1', 'test-nestedlaunch1.exe'),
          debug=False,
          strip=False,
          upx=False,
          console=1 )
