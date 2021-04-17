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
This module contains code useful for doing releases of PyInstaller.

PyInstaller uses package 'zest.releaser' to automate releases. This module
contains mostly customization for the release process.

zest.releaser allows customization by exposing some entry points. For details:

https://zestreleaser.readthedocs.org/en/latest/entrypoints.html
"""

import os
from ..compat import exec_command, getenv


def sign_source_distribution(data):
    """
    Sign the tgz or zip archive that will be uploaded to PYPI.
    :param data:
    """
    print()
    # zest.releaser does a clean checkout where it generates tgz/zip in 'dist'
    # directory and those files will be then uploaded to pypi.
    dist_dir = os.path.join(data['tagdir'], 'dist')
    cmd = ['gpg', '--detach-sign', '--armor']
    if getenv("PYINSTALLER_CODESIGNING_ID"):
        print("Using gpg identity", getenv("PYINSTALLER_CODESIGNING_ID"),
              "for signing.")
        cmd.extend(['--local-user', getenv("PYINSTALLER_CODESIGNING_ID")])
    # Sign all files in 'dist' directory.
    for f in os.listdir(dist_dir):
        f = os.path.join(dist_dir, f)
        print('Signing file %s' % f)
        exec_command(*cmd + [f])
