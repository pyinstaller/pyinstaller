# -*- mode: python -*-

__testname__ = 'test_helloworld_usesystemlibrary'

a = Analysis([__testname__ + '.py'],
             pathex=['.'],
             use_system_library=True)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.'+sys.platform, __testname__ + '.exe'),
          debug=False,
          strip=False,
          upx=False,
          console=True,
          use_system_library=True)
coll = COLLECT( exe,
               a.binaries,
               strip=False,
               upx=False,
               name=os.path.join('dist', __testname__),)
