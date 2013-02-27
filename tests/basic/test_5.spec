# -*- mode: python -*-

__testname__ = 'test_5'

a = Analysis([__testname__ + '.py'],
             pathex=[])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          [('W ignore', '', 'OPTION')],
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.'+sys.platform, __testname__ + '.exe'),
          debug=False,
          strip=False,
          upx=False,
          console=True)
coll = COLLECT( exe,
               a.binaries,
               name=os.path.join('dist', __testname__),)
