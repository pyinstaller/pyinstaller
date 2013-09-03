#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# By default Qt looks for the qml import libraries in the app dir but we can't
# put theme there because of a name clash (on OSX) with the QtQuick dll. So
# they are put in a "qml" directory. Some of the import files are data but
# others are dlls. See hooks/hook-PyQt5.QtQuick.py and the associated 
# support functions in hooks/hookutils.

# Add a runtime hook to tell Qt5 where to find the Qml import libs.

import os
import sys

d = os.path.abspath(os.path.join(sys._MEIPASS, "qml"))

print d

# We replace the QML_IMPORT_PATH variables because we want
# Qt5 to load qml only from the path we set.
if 'QML_IMPORT_PATH' in os.environ:
    del os.environ['QML_IMPORT_PATH']
os.environ['QML_IMPORT_PATH'] = d

if 'QML2_IMPORT_PATH' in os.environ:
    del os.environ['QML2_IMPORT_PATH']
os.environ['QML2_IMPORT_PATH'] = d
