#-----------------------------------------------------------------------------
# Copyright (c) 2014-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Shorten list of hidden imports to what PySide2.QtWebKitWidgets actually
# does link to. It does not need Qml, QSql, or QtQuick.
hiddenimports = ['PySide2.QtCore',
                 'PySide2.QtGui',
                 'PySide2.QtNetwork',
                 'PySide2.QtWebKit'
                 ]
