# -*- mode: python -*-

__testname__ = 'test_buffering'

a = Analysis([os.path.join(HOMEPATH, 'support/_mountzlib.py'), os.path.join(CONFIGDIR, 'support/useUnicode.py'), __testname__ + '.py'],
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
