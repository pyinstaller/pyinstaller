#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import qt_plugins_binaries


# QtMultimedia tries to pull in QtNetwork
hiddenimports = ['PySide2.QtNetwork']

# QtMultimedia needs some plugins
binaries = []
binaries.extend(qt_plugins_binaries('audio', namespace='PySide2'))
binaries.extend(qt_plugins_binaries('mediaservice', namespace='PySide2'))
