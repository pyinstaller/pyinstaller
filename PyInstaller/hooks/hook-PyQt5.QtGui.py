#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


hiddenimports = ['sip', 'PyQt5.QtCore']

from PyInstaller.utils.hooks import qt5_plugins_binaries


binaries = []
binaries.extend(qt5_plugins_binaries('accessible'))
binaries.extend(qt5_plugins_binaries('iconengines'))
binaries.extend(qt5_plugins_binaries('imageformats'))
binaries.extend(qt5_plugins_binaries('inputmethods'))
binaries.extend(qt5_plugins_binaries('graphicssystems'))
binaries.extend(qt5_plugins_binaries('platforms'))
