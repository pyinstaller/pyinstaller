#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.utils.hooks import qt_plugins_binaries

binaries = []
binaries.extend(qt_plugins_binaries('accessible', namespace='PyQt4'))
binaries.extend(qt_plugins_binaries('iconengines', namespace='PyQt4'))
binaries.extend(qt_plugins_binaries('imageformats', namespace='PyQt4'))
binaries.extend(qt_plugins_binaries('inputmethods', namespace='PyQt4'))
binaries.extend(qt_plugins_binaries('graphicssystems', namespace='PyQt4'))

hiddenimports = ['sip', 'PyQt4.QtCore']
