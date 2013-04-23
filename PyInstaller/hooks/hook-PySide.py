#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.compat import is_darwin
from PyInstaller.hooks.hookutils import qt4_menu_nib_dir


# For Qt to work on Mac OS X it is necessary to include directory qt_menu.nib.
# This directory contains some resource files necessary to run PyQt or PySide
# app.
if is_darwin:
    datas = [
        (qt4_menu_nib_dir(), ''),
    ]
