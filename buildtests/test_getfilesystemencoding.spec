# -*- mode: python -*-

__testname__ = 'test_getfilesystemencoding'

a = Analysis(['../support/_mountzlib.py',
              '../support/useUnicode.py',
              'test_getfilesystemencoding.py'],
             pathex=[])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.' + config['target_platform'], __testname__ + '.exe'),
          debug=False,
          strip=False,
          upx=False,
          console=1 )
coll = COLLECT(exe,
               a.binaries,
               strip=False,
               upx=False,
               name=os.path.join('dist', __testname__),)
