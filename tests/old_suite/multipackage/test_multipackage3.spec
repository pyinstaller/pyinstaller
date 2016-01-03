# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# TESTING MULTIPROCESS FEATURE: file A (onedir pack) depends on file B (onefile pack).


__testname__ = 'test_multipackage3'
__testdep__ = 'multipackage3_B'

a = Analysis([__testname__ + '.py'],
             pathex=['.'])
b = Analysis([__testdep__ + '.py'],
             pathex=['.'])

MERGE((b, __testdep__, os.path.join(__testdep__ + '.exe')),
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
        name=os.path.join('dist', __testname__ ))
           
pyzB = PYZ(b.pure)
exeB = EXE(pyzB,
          b.scripts,
          b.binaries,
          b.zipfiles,
          b.datas,
          b.dependencies,
          name=os.path.join('dist', __testdep__ + '.exe'),
          debug=True,
          strip=False,
          upx=True,
          console=1 )

