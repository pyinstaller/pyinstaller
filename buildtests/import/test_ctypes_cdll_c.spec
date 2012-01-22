# -*- mode: python -*-

__testname__ = 'test_ctypes_cdll_c'

a = Analysis([__testname__ + '.py'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.'+sys.platform, __testname__, 
                            __testname__ + '.exe'),
          debug=True,
          strip=False,
          upx=False,
          console=1 )
coll = COLLECT( exe,
               a.binaries,
               a.zipfiles,
               strip=False,
               upx=False,
               name=os.path.join('dist', __testname__))
