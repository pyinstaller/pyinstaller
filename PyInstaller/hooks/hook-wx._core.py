#-----------------------------------------------------------------------------
# Copyright (c) 2019-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for wx._core
# Tested with wxPython 4.0.7 and Cpython 3.7.5

from PyInstaller.utils.hooks import collect_data_files
# from PyInstaller.utils.hooks import collect_submodules

datas = collect_data_files('wx._core')
# hiddenimports = collect_submodules('wx._core')
