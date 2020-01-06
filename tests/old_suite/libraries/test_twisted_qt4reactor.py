#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


# Twisted is an event-driven networking engine.
# 
# This is the test for qt4reactor - Twisted is driven by the Qt mainloop.


import sys


# Workaround to remove the reactor module created by PyInstaller twisted rthook.
# Otherwise you will get error
#   twisted.internet.error.ReactorAlreadyInstalledError: reactor already installed
if 'twisted.internet.reactor' in sys.modules:
    del sys.modules['twisted.internet.reactor']


# Code to init Qt.
from PyQt4 import QtCore
app = QtCore.QCoreApplication(sys.argv)


# Install reactor.
import qt4reactor
qt4reactor.install()


def main():
    """Run application."""
    # Hook up Qt application to Twisted.
    from twisted.internet import reactor

    # Make sure stopping twisted event also shuts down QT.
    reactor.addSystemEventTrigger('after', 'shutdown', app.quit)

    # Shutdown twisted when window is closed.
    app.connect(app, QtCore.SIGNAL("lastWindowClosed()"), reactor.stop)

    # Do not block test to finish.
    reactor.runReturn()


if __name__ == '__main__':
    main()
