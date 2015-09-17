#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
This module contains code useful for doing releases of PyInstaller.

PyInstaller uses package 'zest.releaser' to automate releases. This module
contains mostly customization for the release process.

zest.releaser allows customization by exposing some entry points. For details:

https://zestreleaser.readthedocs.org/en/latest/entrypoints.html
"""


def sign_source_distribution(data):
    """
    Sign the tgz or zip archive that will be uploaded to PYPI.
    :param data:
    """
    print(30 * 'A')
    pass
