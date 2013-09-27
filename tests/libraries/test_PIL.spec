# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


__testname__ = 'test_PIL'

a = Analysis([__testname__ + '.py'],
             pathex=[])
pyz = PYZ(a.pure)

TOC_custom = [('tinysample.tiff','tinysample.tiff','DATA')]

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name=__testname__ + '.exe',
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
