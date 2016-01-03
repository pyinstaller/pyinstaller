#-----------------------------------------------------------------------------
# Copyright (c) 2015-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import sys

if sys.platform == 'darwin':
    d = os.path.join(sys._MEIPASS, 'QtWebEngineProcess.app', 'Contents', 'MacOS', 'QtWebEngineProcess')
    os.environ['QTWEBENGINEPROCESS_PATH'] = d
