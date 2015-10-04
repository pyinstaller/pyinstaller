#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
from pkg_resources import Requirement

from PyInstaller.utils.hooks import qt5_menu_nib_dir, exec_statement
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
qt_version = exec_statement("""
from PyQt5.QtCore import QT_VERSION_STR
print(QT_VERSION_STR)
""")
if is_darwin and qt_version in Requirement.parse("QT<5.4"):
    datas = [
        (qt5_menu_nib_dir(), ''),
    ]
