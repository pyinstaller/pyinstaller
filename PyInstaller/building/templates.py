#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Templates to generate .spec files.
"""

onefiletmplt = """# -*- mode: python -*-
%(cipher_init)s

a = Analysis(%(scripts)s,
             pathex=%(pathex)s,
             binaries=None,
             datas=None,
             hiddenimports=%(hiddenimports)r,
             hookspath=%(hookspath)r,
             runtime_hooks=%(runtime_hooks)r,
             excludes=%(excludes)s,
             win_no_prefer_redirects=%(win_no_prefer_redirects)s,
             win_private_assemblies=%(win_private_assemblies)s,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='%(name)s',
          debug=%(debug)s,
          strip=%(strip)s,
          upx=%(upx)s,
          console=%(console)s %(exe_options)s)
"""

onedirtmplt = """# -*- mode: python -*-
%(cipher_init)s

a = Analysis(%(scripts)s,
             pathex=%(pathex)s,
             binaries=None,
             datas=None,
             hiddenimports=%(hiddenimports)r,
             hookspath=%(hookspath)r,
             runtime_hooks=%(runtime_hooks)r,
             excludes=%(excludes)s,
             win_no_prefer_redirects=%(win_no_prefer_redirects)s,
             win_private_assemblies=%(win_private_assemblies)s,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='%(name)s',
          debug=%(debug)s,
          strip=%(strip)s,
          upx=%(upx)s,
          console=%(console)s %(exe_options)s)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=%(strip)s,
               upx=%(upx)s,
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
