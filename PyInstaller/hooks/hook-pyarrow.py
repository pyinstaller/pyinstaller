#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for https://pypi.org/project/pyarrow/

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

hiddenimports = [
    "pyarrow._parquet",
    "pyarrow.lib",
    "pyarrow.compat",
]

datas = collect_data_files('pyarrow')
binaries = collect_dynamic_libs('pyarrow')
