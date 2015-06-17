#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import sys

# Not neceesary for the code, but informs PyInstaller of the hidden import of QtWebKit, which is performed inside of uic.loadUi.
from PyQt4.QtWebKit import QWebView

from PyQt4.QtGui import QApplication, QDialog
from PyQt4 import uic

# Instead of creating a custom .spec file, assume the .ui file is in the same directory as the source .py file, making it two levels up when frozen.
if getattr(sys, 'frozen', False):
    ui_prefix = '../../'
else:
    ui_prefix = ''

app = QApplication([])
window = QDialog()
uic.loadUi(ui_prefix + 'test_PyQt4-uic.ui', window)
window.show()
#app.exec_()
