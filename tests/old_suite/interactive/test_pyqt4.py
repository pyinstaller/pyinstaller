# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys

from PyQt4 import Qt
from PyQt4 import QtCore
from PyQt4 import QtGui

class MyDialog(QtGui.QDialog):

    def __init__(self):
        super(MyDialog, self).__init__()

        self.label = Qt.QLabel(
            u"Press <ESC> to exit. Some non-ascii chars: řčšěíáŘ",
            self)
        self.setWindowTitle("Hello World from PyQt4")
        self.resize(400, 200)
        self.show()

    def sizeHint(self):
        return self.label.sizeHint()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()


def main():
    app = Qt.QApplication(sys.argv)
    read_formats = ', '.join([unicode(format).lower() \
        for format in QtGui.QImageReader.supportedImageFormats()])
    print(("Qt4 plugin paths: " + unicode(list(app.libraryPaths()))))
    print(("Qt4 image read support: " + read_formats))
    print(('Qt4 Libraries path: ' + unicode(QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.LibrariesPath))))
    ex = MyDialog()
    app.exec_()


if __name__ == "__main__":
    main()
