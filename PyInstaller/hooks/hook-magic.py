#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# hook for https://pypi.org/project/python-magic-bin

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = collect_data_files('magic')
binaries = collect_dynamic_libs('magic')
