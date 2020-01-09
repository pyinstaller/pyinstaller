#-----------------------------------------------------------------------------
# Copyright (c) 2018-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Hook for https://github.com/libtcod/python-tcod
"""
from PyInstaller.utils.hooks import collect_dynamic_libs

hiddenimports = ['_cffi_backend']

# Install shared libraries to the working directory.
binaries = collect_dynamic_libs('tcod', destdir='.')
