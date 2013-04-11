# -*- mode: python -*-

__testname__ = 'test_Image'

a = Analysis([__testname__ + '.py'],
             pathex=[])
pyz = PYZ(a.pure)

TOC_custom = [('tinysample.tiff','tinysample.tiff','DATA')]

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.'+sys.platform, __testname__ + '.exe'),
          debug=True,
          strip=False,
          upx=True,
          console=True )

coll = COLLECT( exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               TOC_custom,
               strip=False,
               upx=True,
               name=os.path.join('dist', __testname__),)
