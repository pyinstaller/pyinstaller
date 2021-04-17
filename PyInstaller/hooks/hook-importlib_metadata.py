#-----------------------------------------------------------------------------
# Copyright (c) 2019-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


"""
importlib_metadata is a library to access the metadata for a Python package.
This functionality intends to replace most uses of pkg_resources entry point
API and metadata API.
"""

from PyInstaller.utils.hooks import copy_metadata

datas = copy_metadata('importlib_metadata')
