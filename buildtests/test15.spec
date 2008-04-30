a = Analysis(['../support/_mountzlib.py',
              '../support/useUnicode.py',
              'test15.py'],
             pathex=[])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name='test15.exe',
          debug=False,
          strip=False,
          upx=False,
          console=1 )
coll = COLLECT( exe,
               a.binaries,
               strip=False,
               upx=False,
               name='disttest15')
