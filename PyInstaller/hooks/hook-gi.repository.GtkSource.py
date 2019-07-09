#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.utils.hooks import collect_glib_share_files, get_gi_typelibs

binaries, datas, hiddenimports = get_gi_typelibs('GtkSource', '3.0')

datas += collect_glib_share_files('gtksourceview-3.0')
