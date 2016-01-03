# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# TESTING MULTIPROCESS FEATURE: file A (onedir pack) depends on file B (onedir pack)
# and file C (onefile pack)


__testname__ = 'test_multipackage5'
__testdep__ = 'multipackage5_B'
__testdep2__ = 'multipackage5_C'

a = Analysis([__testname__ + '.py'],
             pathex=['.'])
b = Analysis([__testdep__ + '.py'],
             pathex=['.'])
c = Analysis([__testdep2__ + '.py'],
             pathex=['.'])


MERGE((b, __testdep__, os.path.join(__testdep__, __testdep__ + '.exe')),
      (c, __testdep2__, os.path.join(__testdep2__ + '.exe')),
      (a, __testname__, os.path.join(__testname__, __testname__ + '.exe')))

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.dependencies,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.'+sys.platform, __testname__,
                            __testname__ + '.exe'),
          debug=True,
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
          name=os.path.join('build', 'pyi.'+sys.platform, __testdep__,
                            __testdep__ + '.exe'),
          debug=True,
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
          debug=True,
          strip=False,
          upx=True,
          console=1 )
