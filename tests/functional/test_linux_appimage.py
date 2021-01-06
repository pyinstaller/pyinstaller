#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
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

# Library imports
# ---------------
import os
import pathlib
import stat
import subprocess
import pytest

from PyInstaller.compat import is_py36


@pytest.mark.linux
@pytest.mark.parametrize('arch', ['x86_64'])
def test_appimage_loading(tmp_path, pyi_builder_spec, arch):
    # Skip the test if appimagetool is not found
    appimagetool = pathlib.Path.home() / ('appimagetool-%s.AppImage' % arch)
    if not is_py36:
        appimagetool = str(appimagetool)
    if not os.path.isfile(appimagetool):
        pytest.skip('%s not found' % appimagetool)

    # Ensure appimagetool is executable
    if not os.access(appimagetool, os.X_OK):
        st = os.stat(appimagetool)
        os.chmod(appimagetool, st.st_mode | stat.S_IXUSR)

    tmp_path = str(tmp_path)  # Fix for Python 3.5

    app_name = 'apptest'
    app_path = os.path.join(tmp_path, '%s-%s.AppImage' % (app_name, arch))

    # Freeze the app
    pyi_builder_spec.test_source('print("OK")', app_name=app_name,
                                 pyi_args=["--onedir"])

    # Prepare the dist folder for AppImage compliancy
    tools_dir = os.path.join(os.path.dirname(__file__), 'data', 'appimage')
    script = os.path.join(tools_dir, 'create.sh')
    subprocess.check_call(['bash', script, tools_dir, tmp_path, app_name])

    # Create the AppImage
    app_dir = os.path.join(tmp_path, 'dist', 'AppRun')
    subprocess.check_call([appimagetool, "--no-appstream", app_dir,
                           app_path])

    # Launch the AppImage
    st = os.stat(app_path)
    os.chmod(app_path, st.st_mode | stat.S_IXUSR)
    subprocess.check_call([app_path])
