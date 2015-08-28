#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Library imports
# ---------------
import sys
import os

# Third-party imports
# -------------------
# Instead of creating a custom .spec file: inform PyInstaller of the
# hidden import of QtWebKit, which is performed inside of uic.loadUi.
from PyQt4.QtWebKit import QWebView
# Other Qt imports used in the code below.
from PyQt4.QtGui import QApplication, QDialog
from PyQt4 import uic
from PyQt4.QtCore import QTimer

# Local imports
# -------------
from pyi_get_datadir import get_data_dir

# Test code
# ---------
app = QApplication([])
window = QDialog()
uic.loadUi(os.path.join(get_data_dir(), 'PyQt4_uic', 'PyQt4-uic.ui'), window)
window.show()
# Exit Qt when the main loop becomes idle.
QTimer.singleShot(0, app.exit)
# Run the main loop, displaying the WebKit widget.
app.exec_()
