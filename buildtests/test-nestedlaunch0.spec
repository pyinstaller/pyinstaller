# -*- mode: python -*-
a = Analysis([os.path.join(HOMEPATH,'support/_mountzlib.py'),
              os.path.join(HOMEPATH,'support/useUnicode.py'), 
              'test-nestedlaunch0.py'],
             pathex=[''])
pyz = PYZ(a.pure)
exe = EXE( pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          name=os.path.join('dist', 'test-nestedlaunch0', 'test-nestedlaunch0.exe'),
          debug=False,
          strip=False,
          upx=False,
          console=1 )
