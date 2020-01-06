#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
import os.path

from PyInstaller.utils.hooks import eval_statement
from PyInstaller.utils.hooks.qt import add_qt5_dependencies, pyqt5_library_info
from PyInstaller.compat import is_win

# Ensure PyQt5 is importable before adding info depending on it.
if pyqt5_library_info.version:
    hiddenimports, binaries, datas = add_qt5_dependencies(__file__)

    # Add libraries needed for SSL if these are available. See issue #3520, #4048.
    if (is_win and eval_statement("""
        from PyQt5.QtNetwork import QSslSocket
        print(QSslSocket.supportsSsl())""")):

        binaries = []
        for dll in ('libeay32.dll', 'ssleay32.dll', 'libssl-1_1-x64.dll',
                    'libcrypto-1_1-x64.dllx'):
            dll_path = os.path.join(pyqt5_library_info.location['BinariesPath'],
                                    dll)
            if os.path.exists(dll_path):
                binaries.append((dll_path, '.'))
