#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.hooks.hookutils import qt5_menu_nib_dir
from PyInstaller.compat import is_darwin


# In the new consolidated mode any PyQt depends on _qt
hiddenimports = ['sip']


# For Qt to work on Mac OS X it is necessary to include directory qt_menu.nib.
# This directory contains some resource files necessary to run PyQt or PySide
# app.
if is_darwin:
    datas = [
        (qt5_menu_nib_dir(), ''),
    ]
