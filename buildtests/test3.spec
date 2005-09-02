a = Analysis(['../support/_mountzlib.py', 'test3.py'],
             pathex=[])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          [('f','','OPTION')],
          exclude_binaries=1,
          name='buildtest3/test3.exe',
          debug=0,
          console=1)
coll = COLLECT( exe,
               a.binaries,
               name='disttest3')
