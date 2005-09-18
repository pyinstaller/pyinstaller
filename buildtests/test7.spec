a = Analysis(['../support/_mountzlib.py', 'test7.py'],
             pathex=[])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name='buildtest7/test7.exe',
          debug=0,
          console=1)
coll = COLLECT( exe,
               a.binaries,
               name='disttest7')
