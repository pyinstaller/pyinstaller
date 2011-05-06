# -*- mode: python -*-

__testname__ = 'test-email'

a = Analysis([os.path.join(HOMEPATH,'support/_mountzlib.py'), os.path.join(HOMEPATH,'support/useUnicode.py'), __testname__ + '.py'],
             pathex=['/home/rasky/src/pyinstaller/buildtests'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build/pyi.linux2/test-email', __testname__ + '.exe'),
          debug=False,
          strip=False,
          upx=False,
          console=1 )
coll = COLLECT( exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name=os.path.join('dist', __testname__))
