config['useZLIB'] = 0
a = Analysis(['../support/_mountzlib.py', 'test2.py'],
             pathex=[],
             hookspath=['hooks1'])
pyz = PYZ(a.pure, level=0)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name='buildtest2/test2.exe',
          icon='test2.ico',
          version='test2-version.txt',
          debug=0,
          console=1)
coll = COLLECT( exe,
               a.binaries - [('zlib','','EXTENSION')],
               name='disttest2')
