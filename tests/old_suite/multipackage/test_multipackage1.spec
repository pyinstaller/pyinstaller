# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# MULTIPROCESS FEATURE: file A (onefile pack) depends on file B (onefile pack).


__testname__ = 'test_multipackage1'
__testdep__ = 'multipackage1_B'

a = Analysis([__testname__ + '.py'],
             pathex=['.'])
b = Analysis([__testdep__ + '.py'],
             pathex=['.'])

pyz = PYZ(a.pure, a.zipped_data,
          b.pure, b.zipped_data,
          append=False)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          a.dependencies,
          name=os.path.join('dist', __testname__ + '.exe'),
          debug=True,
          strip=False,
          upx=False,
          console=1 )
                    
exeB = EXE(pyz,
          b.scripts,
          b.binaries,
          b.zipfiles,
          b.datas,
          b.dependencies,
          name=os.path.join('dist', __testdep__ + '.exe'),
          debug=True,
          strip=False,
          upx=False,
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
        strip=False,
        upx=True,
        name=os.path.join('dist', __testname__))