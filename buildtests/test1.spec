a = Analysis(['../support/_mountzlib.py', 'test1.py'],
             pathex=[],
             hookspath=['hooks1'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name='buildtest1/test1.exe',
          debug=0,
          console=1)
coll = COLLECT( exe,
               a.binaries,
               name='disttest1')
