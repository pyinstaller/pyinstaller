#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from PyQt4 import Qt
from PyQt4 import QtCore
from PyQt4 import QtGui


def main():
    app = Qt.QApplication(sys.argv)
    print(u'Qt4 plugin paths: ' + u', '.join(app.libraryPaths()))
    read_formats = u', '.join(
        [str(img_format).decode('utf-8').lower() for img_format in
         QtGui.QImageReader.supportedImageFormats()])
    print(u'Qt4 image read support: ' + read_formats)
    print(u'Qt4 Libraries path: ' + QtCore.QLibraryInfo.location(
        QtCore.QLibraryInfo.LibrariesPath))
    label = Qt.QLabel(u'Hello World from PyQt4', None)
    label.setWindowTitle(u'Hello World from PyQt4')
    label.resize(300, 300)
    label.show()
    app.exec_()


if __name__ == '__main__':
    main()
