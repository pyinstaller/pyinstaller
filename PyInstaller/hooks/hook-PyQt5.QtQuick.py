#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import os

from PyInstaller.utils import misc
from PyInstaller.utils.hooks import qt5_library_info
from PyInstaller.utils.hooks import add_qt5_dependencies
from PyInstaller import log as logging

logger = logging.getLogger(__name__)

hiddenimports, binaries, datas = add_qt5_dependencies(__file__)

# TODO: we should parse the Qml files to see what we need to import.
dirs = ['Qt',
        #'QtAudioEngine',
        #'QtGraphicalEffects',
        #'QtMultiMedia',
        'QtQml',
        'QtQuick',
        'QtQuick.2',
        #'QtSensors',
        #'QtTest'
]

qmldir = qt5_library_info.location['Qml2ImportsPath']
# Per https://github.com/pyinstaller/pyinstaller/pull/3229#issuecomment-359735031,
# not all PyQt5 installs have QML files. In this case, ``qmldir`` is empty.
if not qmldir:
    logger.warning('Unable to find Qt5 QML files. QML files not packaged.')
else:
    for directory in dirs:
        # Add base qml directories.
        datas += [
            (os.path.join(qmldir, directory),
             os.path.join(qt5_library_info.rel_location['Qml2ImportsPath'],
                          directory)),
        ]

        # Add binaries.
        binaries += [
            (f, os.path.dirname(os.path.relpath(f, qt5_library_info.base_dir)))
            for f in misc.dlls_in_subdirs(os.path.join(qmldir, directory))
        ]
