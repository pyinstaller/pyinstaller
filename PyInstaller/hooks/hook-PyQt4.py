#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os

from PyInstaller.utils.hooks import qt_menu_nib_dir
from PyInstaller.compat import getsitepackages, is_darwin, is_win


# On Windows system PATH has to be extended to point to the PyQt4 directory.
# The PySide directory contains Qt dlls. We need to avoid including different
# version of Qt libraries when there is installed another application (e.g. QtCreator)
if is_win:
    from PyInstaller.utils.win32.winutils import extend_system_path
    extend_system_path([os.path.join(x, 'PyQt4') for x in getsitepackages()])


hiddenimports = ['sip']


# For Qt to work on Mac OS X it is necessary to include directory qt_menu.nib.
# This directory contains some resource files necessary to run PyQt or PySide
# app.
if is_darwin:
    datas = [
        (qt_menu_nib_dir('PyQt4'), 'qt_menu.nib'),
    ]
