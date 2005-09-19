a = Analysis(['../support/_mountzlib.py', 'test6.py'],
             pathex=[])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name='buildtest6/test6.exe',
          debug=0,
          console=1)
coll = COLLECT( exe,
               a.binaries,
               name='disttest6')
