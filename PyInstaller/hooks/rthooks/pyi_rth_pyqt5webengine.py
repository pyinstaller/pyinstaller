#-----------------------------------------------------------------------------
# Copyright (c) 2015-2021, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

import os
import sys

# See ``pyi_rth_qt5.py`: use a "standard" PyQt5 layout.
if sys.platform == 'darwin':
    os.environ['QTWEBENGINEPROCESS_PATH'] = os.path.normpath(os.path.join(
        sys._MEIPASS, 'PyQt5', 'Qt', 'lib',
        'QtWebEngineCore.framework', 'Helpers', 'QtWebEngineProcess.app',
        'Contents', 'MacOS', 'QtWebEngineProcess'
    ))
