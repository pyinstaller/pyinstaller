# -*- mode: python -*-

__testname__ = 'test_python_makefile_onefile'

a = Analysis([__testname__ + '.py'],
             pathex=['.'],
             hiddenimports=[],
             hookspath=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=os.path.join('dist', __testname__),
          debug=True,
          strip=None,
          upx=True,
          console=True )
