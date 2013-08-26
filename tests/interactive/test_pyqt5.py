#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys

from PyQt5 import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets


def main():
    app = QtWidgets.QApplication(sys.argv)
    read_formats = ', '.join([unicode(format).lower() \
        for format in QtGui.QImageReader.supportedImageFormats()])
    print("Qt5 plugin paths: " + unicode(list(app.libraryPaths())))
    print("Qt5 image read support: " + read_formats)
    print('Qt5 Libraries path: ' + \
           unicode(QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.LibrariesPath)))
    label = QtWidgets.QLabel("Hello World from PyQt5", None)
    label.setWindowTitle("Hello World from PyQt5")
    label.resize(300, 300)
    label.show()
    app.exec_()


if __name__ == "__main__":
    main()
