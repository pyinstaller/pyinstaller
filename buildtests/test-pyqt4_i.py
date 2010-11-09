#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from PyQt4 import Qt


def main():
    app = Qt.QApplication(sys.argv)
    label = Qt.QLabel("Hello World from PyQt4", None)
    label.setWindowTitle("Hello World from PyQt4")
    label.show()
    app.exec_()


if __name__ == "__main__":
    main()
