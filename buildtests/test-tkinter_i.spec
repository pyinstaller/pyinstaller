# -*- mode: python -*-
a = Analysis([os.path.join(HOMEPATH,'support/_mountzlib.py'),
              os.path.join(HOMEPATH,'support/useUnicode.py'),
              'test-tkinter_i.py'],
             pathex=['/Users/matteo/Documents/src/pyinstaller/trunk/buildtests'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build/pyi.darwin/test-tkinter_i', 'test-tkinter_i'),
          debug=False,
          strip=False,
          upx=False,
          console=1 )
coll = COLLECT( exe,
               a.binaries,
               a.zipfiles,
               strip=False,
               upx=False,
               name=os.path.join('dist', 'test-tkinter_i'))
