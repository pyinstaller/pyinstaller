#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


hiddenimports = ['sip',
                 'PyQt5.QtCore',
                 'PyQt5.QtQml',
                 'PyQt5.QtGui',
                 'PyQt5.QtNetwork'
                 ]

from PyInstaller.hooks.hookutils import qt5_qml_data, qt5_qml_plugins_binaries

# TODO: we should parse the Qml files to see what we need to import.
dirs = [#'Qt',
        #'QtAudioEngine',
        #'QtGraphicalEffects',
        #'QtMultiMedia',
        'QtQml',
        'QtQuick',
        'QtQuick.2',
        #'QtSensors',
        #'QtTest'
        ]

datas = []
for dir in dirs:
    datas.append(qt5_qml_data(dir))

def hook(mod):
    for dir in dirs:
        mod.binaries.extend(qt5_qml_plugins_binaries(dir))
    return mod
