#-----------------------------------------------------------------------------
# Copyright (c) 2014-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import sys

# The path to Qt's components may not default to the wheel layout for
# self-compiled PyQt5 installations. Mandate the wheel layout. See
# ``utils/hooks/qt.py`` for more details.
pyqt_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt')
os.environ['QT_PLUGIN_PATH'] = os.path.join(pyqt_path, 'plugins')
os.environ['QML2_IMPORT_PATH'] = os.path.join(pyqt_path, 'qml')
