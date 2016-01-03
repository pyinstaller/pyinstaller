#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os

from PyInstaller.utils.hooks import (
    get_module_attribute, is_module_satisfies, qt5_menu_nib_dir)
from PyInstaller.compat import getsitepackages, is_darwin, is_win


# On Windows system PATH has to be extended to point to the PyQt5 directory.
# The PySide directory contains Qt dlls. We need to avoid including different
# version of Qt libraries when there is installed another application (e.g. QtCreator)
if is_win:
    from PyInstaller.utils.win32.winutils import extend_system_path
    extend_system_path([os.path.join(x, 'PyQt5') for x in getsitepackages()])


# In the new consolidated mode any PyQt depends on _qt
hiddenimports = ['sip', 'PyQt5.Qt']


# For Qt<5.4 to work on Mac OS X it is necessary to include `qt_menu.nib`.
# This directory contains some resource files necessary to run PyQt or PySide
# app.
if is_darwin:
    # Version of the currently installed Qt 5.x shared library.
    qt_version = get_module_attribute('PyQt5.QtCore', 'QT_VERSION_STR')
    if is_module_satisfies('Qt < 5.4', qt_version):
        datas = [(qt5_menu_nib_dir(), '')]
