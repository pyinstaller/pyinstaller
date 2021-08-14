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
import os
import shutil

import pytest

from PyInstaller import HOMEPATH, PLATFORM


@pytest.mark.win32
def test_manifest_from_res_file(tmp_path):
    # This import only works on Windows. Place it here, protected by the `@pytest.mark.win32`` decorator.
    from PyInstaller.utils.win32 import winmanifest

    # Locate bootloader executable
    bootloader_file = os.path.join(HOMEPATH, 'PyInstaller', 'bootloader', PLATFORM, 'run.exe')

    # Create a local copy
    test_file = str(tmp_path / 'test_file.exe')
    shutil.copyfile(bootloader_file, test_file)

    # Create a manifest, ...
    manifest_filename = test_file + '.manifest'
    manifest = winmanifest.Manifest(
        type_="win32",
        name='test_file.exe',
        processorArchitecture=winmanifest.processor_architecture(),
        version=(1, 0, 0, 0)
    )
    manifest.filename = manifest_filename
    manifest.requestedExecutionLevel = 'asInvoker'
    manifest.uiAccess = True

    # ... embed it, ...
    manifest.update_resources(test_file, [1])

    # ... and read it back
    manifest2 = winmanifest.ManifestFromResFile(test_file)
    assert manifest == manifest2
