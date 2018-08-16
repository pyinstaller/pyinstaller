#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import os.path

from PyInstaller.utils.hooks import pyqt5_library_info, add_qt5_dependencies
from PyInstaller.compat import is_win

hiddenimports, binaries, datas = add_qt5_dependencies(__file__)

# Add libraries needed for SSL. See issue #3520.
if is_win:
    rel_data_path = ['PyQt5', 'Qt', 'bin']
    binaries += [
        (os.path.join(pyqt5_library_info.location['BinariesPath'],
                      'libeay32.dll'),
         os.path.join(*rel_data_path)),
        (os.path.join(pyqt5_library_info.location['BinariesPath'],
                      'ssleay32.dll'),
         os.path.join(*rel_data_path))
    ]
