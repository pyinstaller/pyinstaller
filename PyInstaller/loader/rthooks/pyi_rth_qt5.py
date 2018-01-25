#-----------------------------------------------------------------------------
# Copyright (c) 2014-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os

# Qt's behavior is controlled by (literally) `hundreds of environment variables
# <https://github.com/pyqt/python-qt5/wiki/Qt-Environment-Variable-Reference>`_,
# any of which could cause a packaged program to misbehave in some odd way.
# Sigh. Remove the most likely culprits.
for e in ('QT_QPA_PLATFORM_PLUGIN_PATH', 'QT_PLUGIN_PATH', 'QML_IMPORT_PATH',
          'QML2_IMPORT_PATH', 'QTWEBENGINEPROCESS_PATH'):
    if e in os.environ:
        # On some platforms (e.g. AIX) 'os.unsetenv()' is not available and then
        # deleting the var from os.environ does not delete it from the
        # environment. In those cases we cannot delete the variable but only set
        # it to the empty string.
        os.environ[e] = ''
        del os.environ[e]
