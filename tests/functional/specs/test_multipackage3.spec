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
__testname__ = 'test_multipackage'
__testdep__ = 'multipackage_B'

names = [__testdep__, __testname__]  # dependency first
types = ["file", "dir"]

analysis = [
    Analysis([os.path.join(SCRIPT_DIR, name + '.py')])
    for name in names]

# Analysis object, name, path of this artifact
merges = [(a, name, (name if t == "file" else os.path.join(name, name)))
          for a, name, t in zip(analysis, names, types)]
MERGE(*merges)

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


for a, name, t in zip(analysis, names, types):
    if t == "file":
        onefile(name, a)
    else:
        onedir(name, a)
