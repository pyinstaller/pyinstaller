#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import qt_plugins_binaries
from PyInstaller.compat import is_linux

hiddenimports = ['PySide2.QtCore']

binaries = []
binaries.extend(qt_plugins_binaries('accessible', namespace='PySide2'))
binaries.extend(qt_plugins_binaries('iconengines', namespace='PySide2'))
binaries.extend(qt_plugins_binaries('imageformats', namespace='PySide2'))
binaries.extend(qt_plugins_binaries('inputmethods', namespace='PySide2'))
binaries.extend(qt_plugins_binaries('graphicssystems', namespace='PySide2'))
binaries.extend(qt_plugins_binaries('platforms', namespace='PySide2'))

if is_linux:
    binaries.extend(qt_plugins_binaries('platformthemes', namespace='PySide2'))
