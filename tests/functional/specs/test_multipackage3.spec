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


# MULTIPROCESS FEATURE: onedir pack depends on onefile pack.
import os

SCRIPT_DIR = 'multipackage-scripts'
__testname__ = 'test_multipackage3'
__testdep__ = 'multipackage3_B'

names = [__testname__, __testdep__]

analysis = [
    Analysis([os.path.join(SCRIPT_DIR, name + '.py')])
    for name in names]

# Analysis object, name, path of this this artifact
MERGE((analysis[1], names[1], names[1]),
      (analysis[0], names[0], os.path.join(names[0], names[0])))

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
onefile(names[1], analysis[1])
