#-----------------------------------------------------------------------------
# Copyright (c) 2014-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os
import glob
from PyInstaller.utils.hooks.qt import add_qt5_dependencies, pyqt5_library_info
from PyInstaller.utils.hooks import remove_prefix, get_module_file_attribute, \
    collect_system_data_files
from PyInstaller.depend.bindepend import getImports
import PyInstaller.compat as compat

# Ensure PyQt5 is importable before adding info depending on it.
if pyqt5_library_info.version is not None:
    hiddenimports, binaries, datas = add_qt5_dependencies(__file__)

    # Include the web engine process, translations, and resources.
    rel_data_path = pyqt5_library_info.qt_rel_dir
    if compat.is_darwin:
        # This is based on the layout of the Mac wheel from PyPi.
        data_path = pyqt5_library_info.location['DataPath']
        libraries = ['QtCore', 'QtWebEngineCore', 'QtQuick', 'QtQml',
                     'QtQmlModels', 'QtNetwork', 'QtGui', 'QtWebChannel',
                     'QtPositioning']
        for i in libraries:
            framework_dir = i + '.framework'
            datas += collect_system_data_files(
                os.path.join(data_path, 'lib', framework_dir),
                os.path.join(rel_data_path, 'lib', framework_dir), True)
        datas += [(os.path.join(data_path, 'lib', 'QtWebEngineCore.framework',
                                'Resources'), os.curdir)]
    else:
        locales = 'qtwebengine_locales'
        resources = 'resources'
        datas += [
            # Gather translations needed by Chromium.
            (os.path.join(pyqt5_library_info.location['TranslationsPath'],
                          locales),
             os.path.join(rel_data_path, 'translations', locales)),
            # Per the `docs <https://doc.qt.io/qt-5.10/qtwebengine-deploying.html#deploying-resources>`_,
            # ``DataPath`` is the base directory for ``resources``.
            (os.path.join(pyqt5_library_info.location['DataPath'], resources),
             os.path.join(rel_data_path, resources)),
            # Include the webengine process. The ``LibraryExecutablesPath`` is only
            # valid on Windows and Linux.
            (os.path.join(pyqt5_library_info.location['LibraryExecutablesPath'],
                          'QtWebEngineProcess*'),
             os.path.join(rel_data_path, remove_prefix(
                pyqt5_library_info.location['LibraryExecutablesPath'],
                pyqt5_library_info.location['PrefixPath'] + '/')))
        ]

    # Add Linux-specific libraries.
    if compat.is_linux:
        # The automatic library detection fails for `NSS
        # <https://packages.ubuntu.com/search?keywords=libnss3>`_, which is used by
        # QtWebEngine. In some distributions, the ``libnss`` supporting libraries
        # are stored in a subdirectory ``nss``. Since ``libnss`` is not statically
        # linked to these, but dynamically loads them, we need to search for and add
        # them.
        #
        # First, get all libraries linked to ``PyQt5.QtWebEngineWidgets``.
        for imp in getImports(get_module_file_attribute('PyQt5.QtWebEngineWidgets')):
            # Look for ``libnss3.so``.
            if os.path.basename(imp).startswith('libnss3.so'):
                # Find the location of NSS: given a ``/path/to/libnss.so``,
                # add ``/path/to/nss/*.so`` to get the missing NSS libraries.
                nss_glob = os.path.join(os.path.dirname(imp), 'nss', '*.so')
                if glob.glob(nss_glob):
                    binaries.append((nss_glob, 'nss'))
