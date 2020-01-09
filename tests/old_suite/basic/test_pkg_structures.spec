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


__testname__ = 'test_pkg_structures'

a = Analysis([__testname__ + '.py'],
        hookspath=['hooks1'])

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name= __testname__ + '.exe',
          icon=__testname__+'.ico',
          version=__testname__+'-version.txt',
          debug=True,
          console=True)

coll = COLLECT( exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               name= __testname__)
