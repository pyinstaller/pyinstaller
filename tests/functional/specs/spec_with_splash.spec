# -----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
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

# If set and 'onefile', a onefile project is built instead of onedir one.
build_mode = os.environ.get('_TEST_SPLASH_BUILD_MODE', 'onedir')

# If set and different from '0', collect tkinter via hidden import.
with_tkinter = os.environ.get('_TEST_SPLASH_WITH_TKINTER', '0')

if with_tkinter != '0':
    # Force tkinter collection via hiddenimports; this simulates a program importing tkinter.
    a = Analysis(
        ['../scripts/pyi_interact_pyi_splash.py'],
        hiddenimports=['tkinter'],
    )
else:
    # On some systems tkinter is included automatically; explicitly exclude it.
    a = Analysis(
        ['../scripts/pyi_interact_pyi_splash.py'],
        excludes=['tkinter', '_tkinter'],
    )

splash = Splash(
    '../data/splash/image.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(10, 50),
    text_color='red',
)

pyz = PYZ(a.pure, a.zipped_data)

if build_mode == 'onefile':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        splash,
        splash.binaries,
        exclude_binaries=False,
        name=app_name,
        debug=True,
        console=True,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        splash,
        exclude_binaries=True,
        name=app_name,
        debug=True,
        console=True,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        splash.binaries,
        name=app_name,
    )
