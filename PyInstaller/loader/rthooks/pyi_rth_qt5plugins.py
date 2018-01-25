#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
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

from PySide2.QtCore import QCoreApplication

# Set "qt5_plugins" as the only path for Qt5 plugins.
QCoreApplication.setLibraryPaths(
    [os.path.abspath(os.path.join(sys._MEIPASS, "qt5_plugins"))])
