#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.hooks.hookutils import exec_statement

mpl_data_dir = exec_statement(
    "import matplotlib; print(matplotlib._get_data_path())")

datas = [
    (mpl_data_dir, ""),
]
