# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys

from PySide import QtCore
from PySide import QtGui


class MyDialog(QtGui.QDialog):
    def __init__(self):
        super(MyDialog, self).__init__()

        self.label = QtGui.QLabel(
            u'Press <ESC> to exit. Some non-ascii chars: řčšěíáŘ'
            u'\nor wait some seconds',
            self)
        self.setWindowTitle('Hello World from PySide')
        self.resize(400, 200)
        self.show()

        # close window after 1.5 seconds
        QtCore.QTimer.singleShot(1500, self.close)

    def sizeHint(self):
        return self.label.sizeHint()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()


def main():
    app = QtGui.QApplication(sys.argv)
    read_formats = ', '.join([str(format).lower() \
                              for format in QtGui.QImageReader.supportedImageFormats()])
    print('Qt4 plugin paths: ' + str(list(app.libraryPaths())))
    print('Qt4 image read support: ' + read_formats)
    print('Qt4 Libraries path: ' + str(
        QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.LibrariesPath)))
    ex = MyDialog()
    app.exec_()


if __name__ == '__main__':
    main()
