# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


# MULTIPACKAGE FEATURE: onedir pack depends on onedir pack and onefile pack
import os
import sys

SCRIPT_DIR = 'multipackage-scripts'
__testname__ = 'test_multipackage5'
__testdep__ = 'multipackage5_B'
__testdep2__ = 'multipackage5_C'

names = [__testname__, __testdep__, __testdep2__]

analysis = [
    Analysis([os.path.join(SCRIPT_DIR, name + '.py')])
    for name in names]

MERGE((analysis[1], names[1], os.path.join(__testdep__, __testdep__)),
      (analysis[2], names[2], os.path.join(__testdep2__)),
      (analysis[0], names[0], os.path.join(__testname__, __testname__)))

def onefile(name, analysis):
    pyz = PYZ(analysis.pure)
    exe = EXE(pyz,
              analysis.scripts,
              analysis.binaries,
              analysis.zipfiles,
              analysis.datas,
              analysis.dependencies,
              name=name,
              debug=True,
              console=True)

def onedir(name, analysis):
    pyz = PYZ(analysis.pure, analysis.zipped_data)
    exe = EXE(pyz,
              analysis.scripts,
              analysis.dependencies,
              exclude_binaries=True,
              name=name,
              debug=True,
              console=True)
    coll = COLLECT(
        exe,
        analysis.binaries,
        analysis.zipfiles,
        analysis.datas,
        name=name)

onedir(names[0], analysis[0])
onedir(names[1], analysis[1])
onefile(names[2], analysis[2])
