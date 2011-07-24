# -*- mode: python -*-

print "TESTING MULTIPROCESS FEATURE: file A (onedir pack) depends on file B (onedir pack) and file C (onefile pack)"

__testname__ = 'test_multipackage5'
__testdep__ = 'multipackage5_B'
__testdep2__ = 'multipackage5_C'

a = Analysis([os.path.join(HOMEPATH,'support', '_mountzlib.py'), os.path.join(CONFIGDIR,'support', 'useUnicode.py'), __testname__ + '.py'],
             pathex=['.'])
b = Analysis([os.path.join(HOMEPATH,'support', '_mountzlib.py'), os.path.join(CONFIGDIR,'support', 'useUnicode.py'), __testdep__ + '.py'],
             pathex=['.'])
c = Analysis([os.path.join(HOMEPATH,'support', '_mountzlib.py'), os.path.join(CONFIGDIR,'support', 'useUnicode.py'), __testdep2__ + '.py'],
             pathex=['.'])


MERGE((b, __testdep__, os.path.join(__testdep__, __testdep__ + '.exe')),
      (c, __testdep2__, os.path.join(__testdep2__ + '.exe')),
      (a, __testname__, os.path.join(__testname__, __testname__ + '.exe')))

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.dependencies,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.' + config['target_platform'], __testname__,__testname__ + '.exe'),
          debug=False,
          strip=False,
          upx=True,
          console=1 )

coll = COLLECT( exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        name=os.path.join('dist', __testname__))

pyzB = PYZ(b.pure)
exeB = EXE(pyzB,
          b.scripts,
          b.dependencies,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.' + config['target_platform'], __testdep__,__testdep__ + '.exe'),
          debug=False,
          strip=False,
          upx=True,
          console=1 )

coll = COLLECT( exeB,
        b.binaries,
        b.zipfiles,
        b.datas,
        strip=False,
        upx=True,
        name=os.path.join('dist', __testdep__))
        
pyzC = PYZ(c.pure)
exeC = EXE(pyzC,
          c.scripts,
          c.binaries,
          c.zipfiles,
          c.datas,
          c.dependencies,
          name=os.path.join('dist', __testdep2__ + '.exe'),
          debug=False,
          strip=False,
          upx=True,
          console=1 )
