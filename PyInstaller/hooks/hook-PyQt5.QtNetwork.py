#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import os.path

from PyInstaller.utils.hooks import eval_statement
from PyInstaller.utils.hooks.qt import add_qt5_dependencies, pyqt5_library_info
from PyInstaller.compat import is_win
from PyInstaller.depend.bindepend import getfullnameof

# Ensure PyQt5 is importable before adding info depending on it.
if pyqt5_library_info.version:
    hiddenimports, binaries, datas = add_qt5_dependencies(__file__)

    # Add libraries needed for SSL if these are available. See issue #3520, #4048.
    if (is_win and eval_statement("""
        from PyQt5.QtNetwork import QSslSocket
        print(QSslSocket.supportsSsl())""")):

        rel_data_path = ['PyQt5', 'Qt', 'bin']
        binaries += [
            # Per http://doc.qt.io/qt-5/ssl.html#enabling-and-disabling-ssl-support,
            # the SSL libraries are dynamically loaded, implying they exist in
            # the system path. Include these.
            (getfullnameof('libeay32.dll'), os.path.join(*rel_data_path)),
            (getfullnameof('ssleay32.dll'), os.path.join(*rel_data_path)),
        ]
