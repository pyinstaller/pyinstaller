#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Library imports
# ---------------
import os

# Third-party imports
# -------------------
# Instead of creating a custom .spec file: inform PyInstaller of the
# hidden import of QtQuickWidgets, which is performed inside of uic.loadUi.
import PyQt5.QtQuickWidgets
# Other Qt imports used in the code below.
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5 import uic
from PyQt5.QtCore import QTimer

# Local imports
# -------------
from pyi_get_datadir import get_data_dir

# Test code
# ---------
app = QApplication([])
window = QDialog()
uic.loadUi(os.path.join(get_data_dir(), 'PyQt5_uic', 'PyQt5-uic.ui'), window)
window.show()
# Exit Qt when the main loop becomes idle.
QTimer.singleShot(0, app.exit)
# Run the main loop, displaying the WebKit widget.
app.exec_()
