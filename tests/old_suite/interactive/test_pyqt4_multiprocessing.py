#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Test of PyQt4 and multiprocessing.
#
# Running this code creates a PyQt4 window in a child process and exits when it
# is closed. If run with the argument 'single', the window is created in the
# same process instead.


import multiprocessing
import sys


def run_qt(title):
    from PyQt4 import QtGui

    app = QtGui.QApplication(sys.argv)
    w = QtGui.QWidget()
    w.setWindowTitle(title)
    w.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    multiprocessing.freeze_support()
    if 'single' in sys.argv:
        run_qt('Same process')
    else:
        p = multiprocessing.Process(target=run_qt, args=('Child process',))
        p.start()
        p.join()
