#-----------------------------------------------------------------------------
# Copyright (c) 2014-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Shorten list of hidden imports to what PyQt5.QtWebKitWidgets actually
# does link to. It does not need Qml, QSql, or QtQuick.
hiddenimports = ["sip",
                 "PyQt5.QtCore",
                 "PyQt5.QtGui",
                 "PyQt5.QtNetwork",
                 "PyQt5.QtWebKit"
                 ]
