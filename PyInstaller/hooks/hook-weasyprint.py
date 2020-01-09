#-----------------------------------------------------------------------------
# Copyright (c) 2015-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Hook for weasyprint: https://pypi.python.org/pypi/WeasyPrint
# Tested on version weasyprint 0.24 using Windows 7 and python 2.7

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('weasyprint')
