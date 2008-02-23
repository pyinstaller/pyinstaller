a = Analysis(['../support/_mountzlib.py', 'test4i.py'],
             pathex=[])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          [('u', '', 'OPTION')],
          exclude_binaries=1,
          name='buildtest4i/test4i.exe',
          debug=0,
          console=1)
coll = COLLECT( exe,
               a.binaries,
               name='disttest4i')
