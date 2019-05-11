#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import os.path

from PyInstaller.utils.hooks import collect_system_data_files
from PyInstaller.utils.hooks.qt import pyside2_library_info, get_qt_binaries

hiddenimports = ['shiboken2']

# Collect the ``qt.conf`` file.
datas = [x for x in
         collect_system_data_files(pyside2_library_info.location['PrefixPath'],
                                   'PySide2')
         if os.path.basename(x[0]) == 'qt.conf']

# Collect required Qt binaries.
binaries = get_qt_binaries(pyside2_library_info)
