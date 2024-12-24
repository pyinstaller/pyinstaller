#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
GNU/Linux-specific test to check the bootloader from the AppImage.
"""

import os
import pathlib
import stat
import subprocess

import pytest


@pytest.mark.linux
@pytest.mark.parametrize('arch', ['x86_64'])
def test_appimage_loading(tmp_path, pyi_builder_spec, arch):
    # Skip the test if appimagetool is not found
    appimagetool = pathlib.Path.home() / f'appimagetool-{arch}.AppImage'
    if not appimagetool.is_file():
        pytest.skip(f'{str(appimagetool)!r} not found')

    # Ensure appimagetool is executable
    if not os.access(appimagetool, os.X_OK):
        st = appimagetool.stat()
        appimagetool.chmod(st.st_mode | stat.S_IXUSR)

    app_name = 'apptest'
    app_path = tmp_path / f'{app_name}-{arch}.AppImage'

    # Freeze the app
    pyi_builder_spec.test_source('print("OK")', app_name=app_name, pyi_args=["--onedir"])

    # Prepare the dist folder for AppImage compliance
    tools_dir = pathlib.Path(__file__).parent / 'data' / 'appimage'
    script = tools_dir / 'create.sh'
    subprocess.check_call(['bash', script, tools_dir, tmp_path, app_name])

    # Create the AppImage
    app_dir = tmp_path / 'dist' / 'AppRun'
    subprocess.check_call([appimagetool, "--no-appstream", app_dir, app_path])

    # Launch the AppImage
    st = app_path.stat()
    app_path.chmod(st.st_mode | stat.S_IXUSR)
    subprocess.check_call([app_path])
