#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
"""
Import hook for PyGObject https://wiki.gnome.org/PyGObject
"""

import os
import os.path
import glob

from PyInstaller.compat import is_win
from PyInstaller.utils.hooks import collect_glib_share_files, collect_glib_etc_files, collect_glib_translations, exec_statement, get_gi_typelibs

binaries, datas, hiddenimports = get_gi_typelibs('Gtk', '3.0')

datas += collect_glib_share_files('fontconfig')
datas += collect_glib_share_files('icons')
datas += collect_glib_share_files('themes')
datas += collect_glib_translations('gtk30')

# these only seem to be required on Windows
if is_win:
    datas += collect_glib_etc_files('fonts')
    datas += collect_glib_etc_files('pango')
    datas += collect_glib_share_files('fonts')
