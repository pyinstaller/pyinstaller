#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_data_files

# pycountry requires the ISO databases for country data.
# Tested v1.15 on Linux/Ubuntu.
# https://pypi.python.org/pypi/pycountry
datas = collect_data_files('pycountry')
