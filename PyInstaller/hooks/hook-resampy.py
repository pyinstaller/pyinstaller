#-----------------------------------------------------------------------------
# Copyright (c) 2015-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for resampy
from PyInstaller.utils.hooks import collect_data_files

# resampy has two data files that need to be included.
datas = collect_data_files('resampy', False)
