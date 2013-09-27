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

# The hello.qml file is put in a resource so that the packaged app can access
# it. To rebuild it use:
# > pyrcc5 pyqt5_qml.qrc > pyqt5_qml_qrc.py
import pyqt5_qml_qrc

def main():
    # This is required so that app.quit can be invoked when the quickview
    # is closed. If it is not present then the app does not exit. It is 
    # possibly a bug in PyQt or Qt.
    global app 
    
    app = QtWidgets.QApplication(sys.argv)
    quickview = QtQuick.QQuickView()
    if getattr(sys, 'frozen', None):
        basedir = sys._MEIPASS
    else:
        basedir = os.path.dirname(__file__)
        
    # The app dir is in the default import path but we can't put the QtQuick
    # import lib dirs there because of a name clash (on OSX) with the QtQuick
    # dll.
    print("Qt5 Qml import paths: " \
                + unicode(quickview.engine().importPathList()))
    quickview.setSource(QtCore.QUrl('qrc:/hello.qml'))
    quickview.engine().quit.connect(app.quit)
    quickview.show()
    
    app.exec_()

if __name__ == "__main__":
    main()
