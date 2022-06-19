#-----------------------------------------------------------------------------
# Copyright (c) 2015-2022, PyInstaller Development Team.
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

# See ``pyi_rth_qt6.py`: use a "standard" PyQt6 layout.
if sys.platform == 'darwin':
    # NOTE: QtWebEngine support was added in Qt6 6.2.x series, so we do not need to worry about pre-6.0.3 path layout.
    pyqt_path = os.path.join(sys._MEIPASS, 'PyQt6', 'Qt6')

    # If QtWebEngineProcess was collected from a framework-based Qt build, we need to set QTWEBENGINEPROCESS_PATH.
    # If not (a dylib-based build; Anaconda on macOS), it should be found automatically, same as on other OSes.
    process_path = os.path.normpath(
        os.path.join(
            pyqt_path, 'lib', 'QtWebEngineCore.framework', 'Helpers', 'QtWebEngineProcess.app', 'Contents', 'MacOS',
            'QtWebEngineProcess'
        )
    )
    if os.path.exists(process_path):
        os.environ['QTWEBENGINEPROCESS_PATH'] = process_path

        # As of Qt 6.3.1, we need to disable sandboxing to make QtWebEngineProcess to work at all with the way
        # PyInstaller currently collects libraries from Qt .framework bundles.
        # This runtime hook should avoid importing PyQt6, so we have no way of querying the version, and always disable
        # sandboxing.
        os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = '1'
