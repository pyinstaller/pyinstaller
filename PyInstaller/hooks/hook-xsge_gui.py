#-----------------------------------------------------------------------------
# Copyright (c) 2016-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for the xsge_gui module: https://pypi.python.org/pypi/xsge_gui

from PyInstaller.utils.hooks import collect_data_files
datas = collect_data_files('xsge_gui')

