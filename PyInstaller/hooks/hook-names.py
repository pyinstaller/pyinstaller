#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# names: generate random names
# Module PyPI Homepage: https://pypi.python.org/pypi/names/0.3.0

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('names')
