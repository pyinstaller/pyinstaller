#-----------------------------------------------------------------------------
# Copyright (c) 2015-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import sys

if sys.platform == 'darwin':
    os.environ['QTWEBENGINEPROCESS_PATH'] = os.path.join(
        sys._MEIPASS, 'Contents', 'Resources', 'PyQt5', 'Qt', 'lib',
        'QtWebEngineCore.framework', 'Helpers'
    )
