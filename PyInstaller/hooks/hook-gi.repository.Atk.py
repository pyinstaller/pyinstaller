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
from PyInstaller.utils.hooks import collect_glib_translations, get_gi_typelibs

binaries, datas, hiddenimports = get_gi_typelibs('Atk', '1.0')
datas += collect_glib_translations('atk10')
