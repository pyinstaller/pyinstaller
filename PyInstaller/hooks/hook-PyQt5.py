#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import os

from PyInstaller.utils.hooks import (get_module_attribute,
    is_module_satisfies, qt_menu_nib_dir, collect_data_files)
from PyInstaller.compat import is_darwin

# In the new consolidated mode any PyQt depends on Qt.
hiddenimports = ['sip', 'PyQt5.Qt']

# Collect just the qt.conf file.
datas = [x for x in collect_data_files('PyQt5', False, os.path.join('Qt', 'bin')) if
         x[0].endswith('qt.conf')]


# For Qt<5.4 to work on Mac OS X it is necessary to include `qt_menu.nib`.
# This directory contains some resource files necessary to run PyQt or PySide
# app.
if is_darwin:
    # Version of the currently installed Qt 5.x shared library.
    qt_version = get_module_attribute('PyQt5.QtCore', 'QT_VERSION_STR')
    if is_module_satisfies('Qt < 5.4', qt_version):
        datas = [(qt_menu_nib_dir('PyQt5'), '')]
