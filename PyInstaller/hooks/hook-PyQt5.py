#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import os

from PyInstaller.utils.hooks import collect_system_data_files
from PyInstaller.utils.hooks.qt import pyqt5_library_info, get_qt_binaries

# Ensure PyQt5 is importable before adding info depending on it.
if pyqt5_library_info.version:
    hiddenimports = [
        # PyQt5.10 and earlier uses sip in an separate package;
        'sip',
        # PyQt5.11 and later provides SIP in a private package. Support both.
        'PyQt5.sip'
    ]

    # Collect the ``qt.conf`` file.
    datas = [x for x in
             collect_system_data_files(pyqt5_library_info.location['PrefixPath'],
                                       'PyQt5')
             if os.path.basename(x[0]) == 'qt.conf']

    # Collect required Qt binaries.
    binaries = get_qt_binaries(pyqt5_library_info)
