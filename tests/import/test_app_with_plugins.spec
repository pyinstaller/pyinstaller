# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


__testname__ = 'test_app_with_plugins'


a = Analysis([__testname__+'.py'], pathex=[])

TOC_custom = [('static_plugin.py','static_plugin.py','DATA')]

pyz = PYZ(a.pure)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=__testname__ + '.exe',
          debug=1,
          console=1)
coll = COLLECT( exe,
               a.binaries,
               TOC_custom,
               name=__testname__)
