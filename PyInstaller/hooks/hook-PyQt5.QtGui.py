#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


hiddenimports = ['sip', 'PyQt5.QtCore']

from PyInstaller.utils.hooks import qt_plugins_binaries
from PyInstaller.compat import is_linux


binaries = []
binaries.extend(qt_plugins_binaries('accessible', namespace='PyQt5'))
binaries.extend(qt_plugins_binaries('iconengines', namespace='PyQt5'))
binaries.extend(qt_plugins_binaries('imageformats', namespace='PyQt5'))
binaries.extend(qt_plugins_binaries('inputmethods', namespace='PyQt5'))
binaries.extend(qt_plugins_binaries('graphicssystems', namespace='PyQt5'))
binaries.extend(qt_plugins_binaries('platforms', namespace='PyQt5'))

if is_linux:
    binaries.extend(qt_plugins_binaries('platformthemes', namespace='PyQt5'))
