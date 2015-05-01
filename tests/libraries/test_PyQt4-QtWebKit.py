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

app = QApplication([])
view = QWebView()
view.show()
#app.exec_()
