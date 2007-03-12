a = Analysis([os.path.join(HOMEPATH,'support', '_mountzlib.py'),
              os.path.join(HOMEPATH,'support', 'useUnicode.py'),
              'test10.py'],
             pathex=['.'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name='buildtest10/test10.exe',
          debug=False,
          strip=False,
          upx=False,
          console=True )
coll = COLLECT( exe,
               a.binaries,
               strip=False,
               upx=False,
               name='disttest10')
