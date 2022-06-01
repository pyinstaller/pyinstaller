#-----------------------------------------------------------------------------
# Copyright (c) 2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os

from PyInstaller.utils import hooks as hookutils


def is_distutils_provided_by_setuptools():
    """
    Check if distutils package is provided by setuptools via its vendored setuptools._distutils sub-package.

    Returns True if setuptools-provided distutils is used, and False if stdlib version is used.
    """
    # Get the package path as parent of its __init__.py file
    distutils_path = os.path.dirname(hookutils.get_module_file_attribute("distutils"))
    # Check the package's directory and its parent directory names
    distutils_name = os.path.basename(distutils_path)
    distutils_parent_name = os.path.basename(os.path.dirname(distutils_path))
    return distutils_name == "_distutils" and distutils_parent_name == "setuptools"
