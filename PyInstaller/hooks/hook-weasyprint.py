#-----------------------------------------------------------------------------
# Copyright (c) 2015-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for weasyprint: https://pypi.python.org/pypi/WeasyPrint
# Tested on version weasyprint 0.24 using Windows 7 and python 2.7

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('weasyprint')
