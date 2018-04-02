#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import os

from PyInstaller.utils import misc
from PyInstaller.utils.hooks import pyqt5_library_info, add_qt5_dependencies
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

qmldir = pyqt5_library_info.location['Qml2ImportsPath']
# Per https://github.com/pyinstaller/pyinstaller/pull/3229#issuecomment-359735031,
# not all PyQt5 installs have QML files. In this case, ``qmldir`` is empty.
if not qmldir:
    logger.warning('Unable to find Qt5 QML files. QML files not packaged.')
else:
    qml_rel_dir = ['PyQt5', 'Qt', 'qml']
    for directory in dirs:
        # Add base qml directories.
        this_qml_dir = os.path.join(qmldir, directory)
        datas += [
            # When Python 3.4 goes EOL (see
            # `PEP 448 <https://www.python.org/dev/peps/pep-0448/>`_, this is
            # better written as ``os.path.join(*qml_rel_dir, directory)``.
            (this_qml_dir, os.path.join(*(qml_rel_dir + [directory]))),
        ]

        # Add binaries.
        binaries += [
            # Produce ``/path/to/Qt/Qml/path_to_qml_binary/qml_binary,
            # PyQt5/Qt/Qml/path_to_qml_binary``. When Python 3.4 goes EOL (see
            # `PEP 448`_, this is better written as
            # ``os.path.join(*qml_rel_dir,
            # os.path.dirname(os.path.relpath(f, qmldir))))``.
            (f, os.path.join(*(qml_rel_dir +
                               [os.path.dirname(os.path.relpath(f, qmldir))])))
            for f in misc.dlls_in_subdirs(this_qml_dir)
        ]
