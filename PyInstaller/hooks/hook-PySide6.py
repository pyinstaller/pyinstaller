#-----------------------------------------------------------------------------
# Copyright (c) 2021-2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks.qt import get_qt_binaries, pyside6_library_info

# Only proceed if PySide6 can be imported.
if pyside6_library_info.version is not None:
    hiddenimports = ['shiboken6', 'inspect']

    # Collect required Qt binaries.
    binaries = get_qt_binaries(pyside6_library_info)
