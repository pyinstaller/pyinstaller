#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os
from PyInstaller.utils.hooks import collect_system_data_files
from PyInstaller.utils.hooks.qt import pyside6_library_info, get_qt_binaries
from PyInstaller.compat import is_win

# Only proceed if PySide6 can be imported.
if pyside6_library_info.version:

    hiddenimports = ['shiboken6']

    # Collect the ``qt.conf`` file.
    if is_win:
        target_qt_conf_dir = ['PySide6']
    else:
        target_qt_conf_dir = ['PySide6', 'Qt']

    datas = [x for x in
             collect_system_data_files(pyside6_library_info.location['PrefixPath'],
                                       os.path.join(*target_qt_conf_dir))
             if os.path.basename(x[0]) == 'qt.conf']

    # Collect required Qt binaries.
    binaries = get_qt_binaries(pyside6_library_info)
