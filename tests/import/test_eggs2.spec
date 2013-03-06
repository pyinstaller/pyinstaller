# -*- mode: python -*-

__testname__ = 'test_eggs2'

a = Analysis([__testname__ + '.py'],
             pathex=['unzipped.egg', 'zipped.egg'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.'+sys.platform, __testname__ + '.exe'),
          debug=0,
          console=1)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               name=os.path.join('dist', __testname__),)
