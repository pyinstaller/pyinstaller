#-----------------------------------------------------------------------------
# Copyright (c) 2014-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import json
import os
from PyInstaller.utils.hooks import add_qt5_dependencies, exec_statement, remove_prefix, get_module_file_attribute
from PyInstaller.depend.bindepend import getImports
import PyInstaller.compat as compat

hiddenimports, binaries, datas = add_qt5_dependencies(__file__)

# Query Qt for paths needed. See http://doc.qt.io/qt-5/qlibraryinfo.html.
q_library_info = json.loads(exec_statement("""
    import json
    from PyQt5.QtCore import QLibraryInfo
    path = QLibraryInfo.location(QLibraryInfo.LibraryExecutablesPath)
    print(str(json.dumps({
      'LibraryExecutablesPath' : QLibraryInfo.location(QLibraryInfo.LibraryExecutablesPath),
      'TranslationsPath' : QLibraryInfo.location(QLibraryInfo.TranslationsPath),
      'PrefixPath' : QLibraryInfo.location(QLibraryInfo.PrefixPath),
      'DataPath' : QLibraryInfo.location(QLibraryInfo.DataPath),
    })))
"""))

# Include the web engine process, translations, and resources.
if compat.is_darwin:
    # This is based on the layout of the Mac wheel from PyPi.
    datas += [
        (os.path.join(q_library_info['DataPath'], 'lib', 'QtWebEngineCore.framework', 'Resources'), os.path.join('PyQt5', 'Qt', 'lib', 'QtWebEngineCore.framework', 'Resources')),
        (os.path.join(q_library_info['DataPath'], 'lib', 'QtWebEngineCore.framework', 'Helpers', 'QtWebEngineProcess.app', 'Contents', 'MacOS', 'QtWebEngineProcess'), os.path.join('PyQt5', 'Qt', 'lib', 'QtWebEngineCore.framework', 'Helpers', 'QtWebEngineProcess.app', 'Contents', 'MacOS')),
    ]
else:
    datas += [
        # Gather translations needed by Chromium.
        (os.path.join(q_library_info['TranslationsPath'], 'qtwebengine_locales'), os.path.join('PyQt5', 'Qt', 'translations', 'qtwebengine_locales')),
        # Per the `docs <https://doc.qt.io/qt-5.10/qtwebengine-deploying.html#deploying-resources>`_, ``DataPath`` is the base directory for ``resources``.
        (os.path.join(q_library_info['DataPath'], 'resources'), os.path.join('PyQt5', 'Qt', 'resources')),
        # Include the webengine process. The ``LibraryExecutablesPath`` is only valid on Windows and Linux.
        (os.path.join(q_library_info['LibraryExecutablesPath'], 'QtWebEngineProcess*'), os.path.join('PyQt5', 'Qt', remove_prefix(q_library_info['LibraryExecutablesPath'], q_library_info['PrefixPath'] + '/')))
]

# Add Linux-specific libraries.
if compat.is_linux:
    # The automatic library detection fails for `NSS <https://packages.ubuntu.com/search?keywords=libnss3>`_, which is used by QtWebEngine.
    #
    # First, find the location of NSS.
    for imp in getImports(get_module_file_attribute('PyQt5.QtWebEngineWidgets')):
        if 'libnss3.so' in os.path.basename(imp):
            # Given a ``/path/to/libnss.so``, add ``/path/to/nss/*.so`` to get the missing NSS libraries.
            binaries.append((os.path.join(os.path.dirname(imp), 'nss', '*.so'), 'nss'))
