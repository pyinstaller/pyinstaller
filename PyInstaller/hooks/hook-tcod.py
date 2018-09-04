#-----------------------------------------------------------------------------
# Copyright (c) 2018-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
"""
Hook for https://github.com/libtcod/python-tcod
"""
from PyInstaller.utils.hooks import collect_dynamic_libs

hiddenimports = ['_cffi_backend']

# Install shared libraries to the working directory.
binaries = collect_dynamic_libs('tcod', destdir='.')
