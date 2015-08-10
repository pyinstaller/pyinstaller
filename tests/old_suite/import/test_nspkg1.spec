# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import glob

__testname__ = 'test_nspkg1'

a = Analysis([__testname__ + '.py'],
             pathex=glob.glob(os.path.join('nspkg1-pkg', '*.egg')),
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)

# This is an additional test: Remove the code-object, modulegraph
# created for. This must be compiler again.
del a.pure._code_cache['nspkg1.bbb.zzz']

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name= __testname__ + '.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name= __testname__)
