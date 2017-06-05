# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import sys

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


pyz = PYZ(a.pure, b.pure, c.pure)

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

exeB = EXE(pyz,
          b.scripts,
          b.dependencies,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.'+sys.platform, __testdep__,
                            __testdep__ + '.exe'),
          debug=True,
          strip=False,
          upx=True,
          console=1 )

exeC = EXE(pyz,
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

coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        exeB,
        b.binaries,
        b.zipfiles,
        b.datas,
        exeC,
        c.binaries,
        c.zipfiles,
        c.datas,
        strip=False,
        upx=True,
        name=os.path.join('dist', __testname__))
