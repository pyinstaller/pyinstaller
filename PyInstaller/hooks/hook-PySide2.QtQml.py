#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
import os

from PyInstaller.utils import misc
from PyInstaller.utils.hooks.qt import pyside2_library_info, add_qt5_dependencies
from PyInstaller import log as logging

# Only proceed if PySide2 can be imported.
if pyside2_library_info.version is not None:
    logger = logging.getLogger(__name__)

    hiddenimports, binaries, datas = add_qt5_dependencies(__file__)

    qmldir = pyside2_library_info.location['Qml2ImportsPath']
    # Not all PySide2 installs have QML files. In this case, ``qmldir`` is empty. In
    # addition, the directory may not exist even if ``qmldir`` is not empty.
    if not os.path.exists(qmldir):
        logger.warning('Unable to find Qt5 QML files. QML files not packaged.')
    else:
        qml_rel_dir = ['PySide2', 'qml']
        datas += [(qmldir, os.path.join(*qml_rel_dir))]
        binaries += [
            # Produce ``/path/to/Qt/Qml/path_to_qml_binary/qml_binary,
            # PyQt5/Qt/Qml/path_to_qml_binary``. When Python 3.4 goes EOL (see
            # PEP 448), this is better written as
            # ``os.path.join(*qml_rel_dir,
            # os.path.dirname(os.path.relpath(f, qmldir))))``.
            (f, os.path.join(*(qml_rel_dir +
                               [os.path.dirname(os.path.relpath(f, qmldir))])))
            for f in misc.dlls_in_subdirs(qmldir)
        ]
