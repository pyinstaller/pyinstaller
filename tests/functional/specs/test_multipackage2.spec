# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


# MULTIPROCESS FEATURE: file A (onefile pack) depends on file B (onedir pack)
import os
import sys

SCRIPT_DIR = 'multipackage-scripts'
__testname__ = 'test_multipackage2'
__testdep__ = 'multipackage2_B'

a = Analysis([os.path.join(SCRIPT_DIR, __testname__ + '.py')],
             hookspath=[os.path.join(SPECPATH, SCRIPT_DIR, 'extra-hooks')],
             pathex=['.'])
b = Analysis([os.path.join(SCRIPT_DIR, __testdep__ + '.py')],
             hookspath=[os.path.join(SPECPATH, SCRIPT_DIR, 'extra-hooks')],
             pathex=['.'])

MERGE((b, __testdep__, os.path.join(__testdep__, __testdep__)),
      (a, __testname__, __testname__))

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          a.dependencies,
          name=os.path.join('dist', __testname__),
          debug=True,
          strip=False,
          upx=True,
          console=1 )

pyzB = PYZ(b.pure)
exeB = EXE(pyzB,
          b.scripts,
          b.dependencies,
          exclude_binaries=1,
          name=os.path.join('build', 'pyi.'+sys.platform, __testdep__,
                            __testdep__),
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

