#-----------------------------------------------------------------------------
# Copyright (c) 2019-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import json
import os
import sys

from PyQt5.QtCore import QObject, QEvent, QTimer
from PyQt5.QtWidgets import QWidget, QApplication, qApp


class EventHandler(QObject):
    def __init__(self, logfile, parent=None):
        super().__init__(parent=parent)
        assert isinstance(logfile, str) and logfile
        self.logfile = logfile
        self.activate_count = 0

    def eventFilter(self, obj, event):
        """
        This event filter just logs the URLs it receives as FileOpen events to self.logfile
        """
        try:
            if event.type() == QEvent.FileOpen:
                with open(self.logfile, 'a') as file:
                    file.write("url {}\n".format(event.url().toString()))
                    file.write("activate_count {}\n".format(self.activate_count))
                qApp.quit()  # Tell app to quit after receiving this event
                return True
            elif event.type() == QEvent.ApplicationActivate:
                self.activate_count += 1
        except Exception as e:
            print("Caught exception in eventFilter exception: " + repr(e), file=sys.stderr)
        return super().eventFilter(obj, event)

    def log_started(self):
        try:
            with open(self.logfile, 'wt') as file:
                file.write("started {}\n".format(json.dumps({"argv": sys.argv})))
        except Exception as e:
            print(
                "Caught exception while attempting to write/open",
                self.logfile,
                "exception: " + repr(e),
                file=sys.stderr
            )
            qApp.quit()


def main():
    basedir = os.path.dirname(sys.executable)
    # if script is inside .app package
    if os.path.basename(basedir) == 'MacOS':
        basedir = os.path.abspath(os.path.join(basedir, os.pardir, os.pardir, os.pardir))

    logfile = os.path.join(basedir, 'events.log')

    app = QApplication(list(sys.argv))  # Copy args to prevent qApp modifying
    dummy = QWidget()
    dummy.showMinimized()
    app.setQuitOnLastWindowClosed(False)
    eh = EventHandler(logfile=logfile)
    app.installEventFilter(eh)
    # Log that we did start so the calling app knows
    QTimer.singleShot(0, eh.log_started)
    timeout = 7000  # Default 7 seconds
    try:
        # Last arg is timeout (may be passed-in from test script)
        timeout = int(1000 * float(sys.argv[-1]))
    except (ValueError, IndexError):
        # Arg was missing or bad arg, use default
        pass
    # Quit the app after timeout milliseconds if we never get the event
    QTimer.singleShot(timeout, app.quit)
    app.exec_()


if __name__ == '__main__':
    main()
