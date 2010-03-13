# -*- mode: python -*-

__testname__ = 'test4i'

a = Analysis(['../support/_mountzlib.py', 'test4i.py'],
             pathex=[])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          [('u', '', 'OPTION')],
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.' + config['target_platform'], __testname__ + '.exe'),
          debug=0,
          console=1)
coll = COLLECT( exe,
               a.binaries,
               name=os.path.join('dist', __testname__),)
