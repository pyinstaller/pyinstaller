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
import sys

# substituted by test-case
app_name = "@APPNAME@"
script_name = '@SCRIPTDIR@/pyi_symlink_basename_is_kept.py'

# ensure substitutes are done
assert app_name != ("@APP" + "NAME@"), \
    "APPNAME was not substituted in spec-file"
assert not script_name.startswith("@SCRIPT" + "DIR@/"), \
    "SCRIPTDIR was not substituted in spec-file"

symlink_name =  app_name + "_1"

a = Analysis([script_name])

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name=app_name,
          debug=False, # the test is this .spec-file
          console=True)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               name=app_name)

os.symlink(app_name,
           os.path.join(DISTPATH, app_name, symlink_name))
