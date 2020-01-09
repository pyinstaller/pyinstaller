#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


"""
Templates to generate .spec files.
"""

onefiletmplt = """# -*- mode: python ; coding: utf-8 -*-
%(cipher_init)s

a = Analysis(%(scripts)s,
             pathex=%(pathex)s,
             binaries=%(binaries)s,
             datas=%(datas)s,
             hiddenimports=%(hiddenimports)r,
             hookspath=%(hookspath)r,
             runtime_hooks=%(runtime_hooks)r,
             excludes=%(excludes)s,
             win_no_prefer_redirects=%(win_no_prefer_redirects)s,
             win_private_assemblies=%(win_private_assemblies)s,
             cipher=block_cipher,
             noarchive=%(noarchive)s)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          %(options)s,
          name='%(name)s',
          debug=%(debug_bootloader)s,
          bootloader_ignore_signals=%(bootloader_ignore_signals)s,
          strip=%(strip)s,
          upx=%(upx)s,
          upx_exclude=%(upx_exclude)s,
          runtime_tmpdir=%(runtime_tmpdir)r,
          console=%(console)s %(exe_options)s)
"""

onedirtmplt = """# -*- mode: python ; coding: utf-8 -*-
%(cipher_init)s

a = Analysis(%(scripts)s,
             pathex=%(pathex)s,
             binaries=%(binaries)s,
             datas=%(datas)s,
             hiddenimports=%(hiddenimports)r,
             hookspath=%(hookspath)r,
             runtime_hooks=%(runtime_hooks)r,
             excludes=%(excludes)s,
             win_no_prefer_redirects=%(win_no_prefer_redirects)s,
             win_private_assemblies=%(win_private_assemblies)s,
             cipher=block_cipher,
             noarchive=%(noarchive)s)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          %(options)s,
          exclude_binaries=True,
          name='%(name)s',
          debug=%(debug_bootloader)s,
          bootloader_ignore_signals=%(bootloader_ignore_signals)s,
          strip=%(strip)s,
          upx=%(upx)s,
          console=%(console)s %(exe_options)s)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=%(strip)s,
               upx=%(upx)s,
               upx_exclude=%(upx_exclude)s,
               name='%(name)s')
"""

cipher_absent_template = """
block_cipher = None
"""

cipher_init_template = """
block_cipher = pyi_crypto.PyiBlockCipher(key=%(key)r)
"""

bundleexetmplt = """app = BUNDLE(exe,
             name='%(name)s.app',
             icon=%(icon)s,
             bundle_identifier=%(bundle_identifier)s)
"""

bundletmplt = """app = BUNDLE(coll,
             name='%(name)s.app',
             icon=%(icon)s,
             bundle_identifier=%(bundle_identifier)s)
"""
