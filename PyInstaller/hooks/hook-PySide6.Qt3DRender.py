#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)

# In PySide 6.7.0, Qt3DRender module added a reference to QtOpenGL type system. The hidden import is required on
# Windows, while on macOS and Linux we seem to pick it up automatically due to the corresponding Qt shared library
# appearing among binary dependencies. Keep it around on all OSes, though - just in case this ever changes.
if pyside6_library_info.version is not None and pyside6_library_info.version >= [6, 7]:
    hiddenimports += ['PySide6.QtOpenGL']
