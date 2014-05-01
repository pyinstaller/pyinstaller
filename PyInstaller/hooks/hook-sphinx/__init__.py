#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from hookutils import collect_submodules, collect_data_files

hiddenimports = collect_submodules('sphinx.ext')
datas = collect_data_files('sphinx')
