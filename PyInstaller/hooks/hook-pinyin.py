#-----------------------------------------------------------------------------
# Copyright (c) 2017-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for the pinyin package: https://pypi.python.org/pypi/pinyin
# Tested with pinyin 0.4.0 and Python 3.6.2, on Windows 10 x64.

from PyInstaller.utils.hooks import collect_data_files

# pinyin relies on 'Mandarin.dat' and 'cedict.txt.gz'
# for character and word translation.
datas = collect_data_files('pinyin')
