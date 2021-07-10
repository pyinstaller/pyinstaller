#-----------------------------------------------------------------------------
# Copyright (c) 2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
from PyInstaller.utils.hooks.qt import pyside6_library_info, \
    get_qt_binaries, get_qt_conf_file

# Only proceed if PySide6 can be imported.
if pyside6_library_info.version is not None:
    hiddenimports = ['shiboken6']

    # Collect the ``qt.conf`` file.
    datas = get_qt_conf_file(pyside6_library_info)

    # Collect required Qt binaries.
    binaries = get_qt_binaries(pyside6_library_info)
