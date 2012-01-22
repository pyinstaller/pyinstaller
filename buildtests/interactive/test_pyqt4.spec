# -*- mode: python -*-

__testname__ = 'test_pyqt4'

a = Analysis([__testname__ + '.py'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.'+sys.platform, __testname__, 
                            __testname__ + '.exe'),
          debug=False,
          strip=False,
          upx=False,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name=os.path.join('dist', __testname__))
               
import sys
if sys.platform.startswith("darwin"):
    app = BUNDLE(coll,
        name=os.path.join('dist', __testname__ + '.app'),
        version='0.0.1')
