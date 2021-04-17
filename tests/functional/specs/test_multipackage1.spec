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


# MULTIPROCESS FEATURE: file A (onefile pack) depends on file B (onefile pack).
import os

SCRIPT_DIR = 'multipackage-scripts'
__testname__ = 'test_multipackage1'
__testdep__ = 'multipackage1_B'

a = Analysis([os.path.join(SCRIPT_DIR, __testname__ + '.py')],
             hookspath=[os.path.join(SPECPATH, SCRIPT_DIR, 'extra-hooks')],
             pathex=['.'])
b = Analysis([os.path.join(SCRIPT_DIR, __testdep__ + '.py')],
             hookspath=[os.path.join(SPECPATH, SCRIPT_DIR, 'extra-hooks')],
             pathex=['.'])

MERGE((b, __testdep__, __testdep__), (a, __testname__, __testname__))

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
          upx=False,
          console=1 )

pyzB = PYZ(b.pure)
exeB = EXE(pyzB,
          b.scripts,
          b.binaries,
          b.zipfiles,
          b.datas,
          b.dependencies,
          name=os.path.join('dist', __testdep__),
          debug=True,
          strip=False,
          upx=False,
          console=1 )

