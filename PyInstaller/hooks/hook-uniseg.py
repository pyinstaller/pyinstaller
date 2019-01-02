#-----------------------------------------------------------------------------
# Copyright (c) 2017-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for the uniseg module: https://pypi.python.org/pypi/uniseg

from PyInstaller.utils.hooks import collect_data_files
datas = collect_data_files('uniseg')
