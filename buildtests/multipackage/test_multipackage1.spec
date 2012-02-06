# -*- mode: python -*-

'''
MULTIPROCESS FEATURE: file A (onefile pack) depends on file B (onefile pack).
'''

__testname__ = 'test_multipackage1'
__testdep__ = 'multipackage1_B'

a = Analysis([__testname__ + '.py'],
             pathex=['.'])
b = Analysis([__testdep__ + '.py'],
             pathex=['.'])

MERGE((b, __testdep__, __testdep__ + '.exe'), (a, __testname__, __testname__ + '.exe'))

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          a.dependencies,
          name=os.path.join('dist', __testname__ + '.exe'),
          debug=False,
          strip=False,
          upx=True,
          console=1 )
                    
pyzB = PYZ(b.pure)
exeB = EXE(pyzB,
          b.scripts,
          b.binaries,
          b.zipfiles,
          b.datas,
          b.dependencies,
          name=os.path.join('dist', __testdep__ + '.exe'),
          debug=False,
          strip=False,
          upx=True,
          console=1 )

