#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyQt4.QtGui import QApplication
from PyQt4.QtWebKit import QWebView
from PyQt4.QtCore import QTimer

app = QApplication([])
view = QWebView()
view.show()
# Exit Qt when the main loop becomes idle.
QTimer.singleShot(0, app.exit)
# Run the main loop, displaying the WebKit widget.
app.exec_()
