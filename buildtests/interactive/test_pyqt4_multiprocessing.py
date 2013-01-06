#
# Copyright (C) 2012-2013
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA


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
