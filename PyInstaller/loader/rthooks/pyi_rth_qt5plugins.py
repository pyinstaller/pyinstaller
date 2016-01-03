#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Qt5 plugins are bundled as data files (see hooks/hook-PyQt5*),
# within a "qt5_plugins" directory.
# We add a runtime hook to tell Qt5 where to find them.

import os
import sys

d = "qt5_plugins"
d = os.path.join(sys._MEIPASS, d)


# We remove QT_PLUGIN_PATH variable, because we want Qt5 to load
# plugins only from one path.
if 'QT_PLUGIN_PATH' in os.environ:
    # On some platforms (e.g. AIX) 'os.unsetenv()' is not available and then
    # deleting the var from os.environ does not delete it from the environment.
    # In those cases we cannot delete the variable but only set it to the
    # empty string.
    os.environ['QT_PLUGIN_PATH'] = ''
    del os.environ['QT_PLUGIN_PATH']

try:
    import sip
except ImportError:
    # The packaging system may name sip PyQt5.sip, so make it available as "sip"
    try:
        import PyQt5.sip as sip
        sys.modules['sip'] = sip
    except ImportError:
        pass  # if this didn't work, there will be a NameError later


# We cannot use QT_PLUGIN_PATH here, because it would not work when
# PyQt5 is compiled with a different CRT from Python (eg: it happens
# with Riverbank's GPL package).
from PyQt5.QtCore import QCoreApplication
# We set "qt5_plugins" as only one path for Qt5 plugins
QCoreApplication.setLibraryPaths([os.path.abspath(d)])
