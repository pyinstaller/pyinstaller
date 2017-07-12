#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Qt4 plugins are bundled as data files (see hooks/hook-PyQt4*),
# within a "qt4_plugins" directory.
# We add a runtime hook to tell Qt4 where to find them.

import os
import sys

d = "qt4_plugins"
d = os.path.join(sys._MEIPASS, d)


# We remove QT_PLUGIN_PATH variable, beasuse we want Qt4 to load
# plugins only from one path.
if 'QT_PLUGIN_PATH' in os.environ:
    # On some platforms (e.g. AIX) 'os.unsetenv()' is not available and then
    # deleting the var from os.environ does not delete it from the environment.
    # In those cases we cannot delete the variable but only set it to the
    # empty string.
    os.environ['QT_PLUGIN_PATH'] = ''
    del os.environ['QT_PLUGIN_PATH']


# We cannot use QT_PLUGIN_PATH here, because it would not work when
# PyQt4 is compiled with a different CRT from Python (eg: it happens
# with Riverbank's GPL package).

# Suppose that the user usually does not use both (PySide and PyQt4)
# in the same app.
# First try importing PySide and then fallback to PyQt4.
try:
    from PySide.QtCore import QCoreApplication
except ImportError:
    from PyQt4.QtCore import QCoreApplication

# We set "qt4_plugins" as only one path for Qt4 plugins
QCoreApplication.setLibraryPaths([os.path.abspath(d)])
