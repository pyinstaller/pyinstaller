#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys
import os

from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtQuick

def main():
    # This is required so that app.quit can be invoked
    # when the quickview is closed. 
    global app 
    
    app = QtWidgets.QApplication(sys.argv)
    quickview = QtQuick.QQuickView()
    if getattr(sys, 'frozen', None):
        basedir = sys._MEIPASS
    else:
        basedir = os.path.dirname(__file__)
    quickview.setSource(QtCore.QUrl.fromLocalFile(
                                    os.path.join(basedir,'hello.qml')))
    quickview.engine().quit.connect(app.quit)
    quickview.show()
    
    app.exec_()

if __name__ == "__main__":
    main()
