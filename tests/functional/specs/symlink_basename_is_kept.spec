# -*- coding: utf-8 ; mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os

# substituted by test-case
script_name = '@SCRIPTDIR@/pyi_symlink_basename_is_kept.py'
symlink_name =  "@SYMLINKNAME@_1"

# ensure substitutes are done
assert not symlink_name.startswith("@SYMLINK" + "NAME@_"), \
    "SYMLINKNAME was not substituted in spec-file"
assert not script_name.startswith("@SCRIPT" + "DIR@/"), \
    "SCRIPTDIR was not substituted in spec-file"

app_name = "keep_symlink_basename"

a = Analysis([script_name])

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=app_name,
          strip=False,
          debug=False, # the test is this .spec-file
          console=True)

os.symlink(app_name, os.path.join(DISTPATH, symlink_name))
