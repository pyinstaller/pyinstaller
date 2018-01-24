#-----------------------------------------------------------------------------
# Copyright (c) 2014-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
from PyInstaller.utils.hooks import add_qt5_dependencies, \
    get_module_file_attribute, qt5_library_info
from PyInstaller.depend.bindepend import getImports
import PyInstaller.compat as compat

hiddenimports, binaries, datas = add_qt5_dependencies(__file__)

# Include the web engine process, translations, and resources.
if compat.is_darwin:
    # This is based on the layout of the Mac wheel from PyPi.
    data_path = qt5_library_info.location['DataPath']
    rel_data_path = qt5_library_info.rel_location['DataPath']
    resources = 'lib', 'QtWebEngineCore.framework', 'Resources'
    web_engine_process = ('lib', 'QtWebEngineCore.framework', 'Helpers',
                          'QtWebEngineProcess.app', 'Contents', 'MacOS')
    datas += [
        (os.path.join(data_path, *resources),
         os.path.join(rel_data_path, *resources)),
        (os.path.join(data_path, *web_engine_process, 'QtWebEngineProcess'),
         os.path.join(rel_data_path, *web_engine_process)),
    ]
else:
    locales = 'qtwebengine_locales'
    resources = 'resources'
    datas += [
        # Gather translations needed by Chromium.
        (os.path.join(qt5_library_info.location['TranslationsPath'],
                      locales),
         os.path.join(qt5_library_info.rel_location['TranslationsPath'],
                      locales)),
        # Per the `docs <https://doc.qt.io/qt-5.10/qtwebengine-deploying.html#deploying-resources>`_,
        # ``DataPath`` is the base directory for ``resources``.
        (os.path.join(qt5_library_info.location['DataPath'], resources),
         os.path.join(qt5_library_info.rel_location['DataPath'], resources)),
        # Include the webengine process. The ``LibraryExecutablesPath`` is only
        # valid on Windows and Linux.
        (os.path.join(qt5_library_info.location['LibraryExecutablesPath'],
                      'QtWebEngineProcess*'),
         qt5_library_info.rel_location['LibraryExecutablesPath'])
    ]

# Add Linux-specific libraries.
if compat.is_linux:
    # The automatic library detection fails for `NSS
    # <https://packages.ubuntu.com/search?keywords=libnss3>`_, which is used by
    # QtWebEngine.
    #
    # First, find the location of NSS.
    for imp in getImports(get_module_file_attribute('PyQt5.QtWebEngineWidgets')):
        if 'libnss3.so' in os.path.basename(imp):
            # Given a ``/path/to/libnss.so``, add ``/path/to/nss/*.so`` to get
            # the missing NSS libraries.
            binaries.append((os.path.join(os.path.dirname(imp), 'nss', '*.so'),
                             'nss'))
