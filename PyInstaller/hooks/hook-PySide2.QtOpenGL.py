#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import qt_plugins_binaries
from PyInstaller.compat import is_linux

hiddenimports = ['PySide2.QtCore',
                 'PySide2.QtWidgets',
                 'PySide2.QtGui']

binaries = []

if is_linux:
    binaries.extend(qt_plugins_binaries('xcbglintegrations', namespace='PySide2'))
