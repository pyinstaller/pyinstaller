#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
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


def main():
    app = Qt.QApplication(sys.argv)
    read_formats = ', '.join([unicode(format).lower() \
        for format in QtGui.QImageReader.supportedImageFormats()])
    print("Qt4 plugin paths: " + unicode(list(app.libraryPaths())))
    print("Qt4 image read support: " + read_formats)
    print('Qt4 Libraries path: ' + unicode(QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.LibrariesPath)))
    label = Qt.QLabel("Hello World from PyQt4", None)
    label.setWindowTitle("Hello World from PyQt4")
    label.resize(300, 300)
    label.show()
    app.exec_()


if __name__ == "__main__":
    main()
