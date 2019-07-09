#-----------------------------------------------------------------------------
# Copyright (c) 2015-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for appy.pod: https://pypi.python.org/pypi/appy/0.9.1

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('appy.pod', True)
