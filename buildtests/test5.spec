a = Analysis(['../support/_mountzlib.py', 'test5.py'],
             pathex=[])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          [('W ignore', '', 'OPTION')],
          exclude_binaries=1,
          name='buildtest5/test5.exe',
          debug=0,
          console=1)
coll = COLLECT( exe,
               a.binaries,
               name='disttest5')
