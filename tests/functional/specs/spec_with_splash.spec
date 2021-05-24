# -----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------
import os

app_name = "spec_with_splash"

# If set and not None, a onefile project is built
onefile = os.environ.get('_TEST_SPLASH_ONEFILE', None)

# To prevent that on some systems tkinter is included automatically
# we exclude it specifically
a = Analysis(['../scripts/pyi_interact_pyi_splash.py'],
             excludes=['tkinter', '_tkinter'])

splash = Splash('../data/splash/image.png',
                binaries=a.binaries,
                datas=a.datas,
                text_pos=(10, 50),
                text_color='red')

pyz = PYZ(a.pure, a.zipped_data)

if onefile:
     exe = EXE(pyz,
               a.scripts,
               a.binaries,
               a.zipfiles,
               a.datas,
               splash,
               splash.binaries,
               exclude_binaries=False,
               name=app_name,
               debug=True,
               console=True)

else:
     exe = EXE(pyz,
               a.scripts,
               splash,
               exclude_binaries=True,
               name=app_name,
               debug=True,
               console=True)
     coll = COLLECT(exe,
                    a.binaries,
                    a.zipfiles,
                    a.datas,
                    splash.binaries,
                    name=app_name)
