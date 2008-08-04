# -*- mode: python -*-

__testname__ = 'test8'

a = Analysis([os.path.join(HOMEPATH,'support', '_mountzlib.py'),
              os.path.join(HOMEPATH,'support', 'useUnicode.py'),
              'test8.py'],
             pathex=['.'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.' + config['target_platform'], __testname__ + '.exe'),
          debug=0,
          strip=0,
          upx=0,
          console=1 )
coll = COLLECT( exe,
               a.binaries,
               strip=0,
               upx=0,
               name=os.path.join('dist', __testname__),)
