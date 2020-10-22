#-----------------------------------------------------------------------------
# Copyright (c) 2019-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os
import sys

from PyQt5.QtCore import QObject, QEvent, QTimer
from PyQt5.QtWidgets import QWidget, QApplication, qApp


class EventHandler(QObject):
    logfile = None

    def eventFilter(self, obj, event):
        """ This event filter just logs the URLs it receives as FileOpen
        events to self.logfile """
        assert self.logfile
        if event.type() == QEvent.FileOpen:
            try:
                with open(self.logfile, 'at') as file:
                    file.write(event.url().toString() + "\n")
                return True
            except Exception as e:
                print("Caught exception while attempting to write/open",
                      self.logfile, "exception: " + repr(e), file=sys.stderr)
            qApp.quit()  # Quit after receiving the event
        return False

    def log_started(self):
        assert self.logfile
        try:
            with open(self.logfile, 'wt') as file:
                file.write("started\n")
        except Exception as e:
            print("Caught exception while attempting to write/open",
                  self.logfile, "exception: " + repr(e), file=sys.stderr)
            qApp.quit()


def main():
    basedir = os.path.dirname(sys.executable)
    # if script is inside .app package
    if os.path.basename(basedir) == 'MacOS':
        basedir = os.path.abspath(
            os.path.join(basedir, os.pardir, os.pardir, os.pardir))

    logfile = os.path.join(basedir, 'events.log')

    app = QApplication(sys.argv)
    dummy = QWidget()
    dummy.hide()
    app.setQuitOnLastWindowClosed(False)
    eh = EventHandler()
    eh.logfile = logfile
    app.installEventFilter(eh)
    # Log that we did start so the calling app knows
    QTimer.singleShot(0, eh.log_started)
    timeout = 5000  # Default 5 seconds
    try:
        # Last arg is timeout (may be passed-in from test script)
        timeout = int(1000 * float(sys.argv[-1]))
    except (ValueError, IndexError):
        """Arg was missing or bad arg, use default"""
    # Quit the app after timeout milliseconds if we never get the event
    QTimer.singleShot(timeout, app.quit)
    app.exec_()


if __name__ == '__main__':
    main()
