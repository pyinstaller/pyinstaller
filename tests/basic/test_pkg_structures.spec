# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
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
          debug=0,
          console=1)

coll = COLLECT( exe,
               a.binaries,
               name= __testname__)
