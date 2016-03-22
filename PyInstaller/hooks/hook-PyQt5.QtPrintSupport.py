#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


hiddenimports = ['sip', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets']

from PyInstaller.utils.hooks import qt_plugins_binaries


binaries = []
binaries.extend(qt_plugins_binaries('printsupport', namespace='PyQt5'))
