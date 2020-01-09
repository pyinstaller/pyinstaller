#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Hook for the openpyxl module: https://pypi.python.org/pypi/openpyxl
# Tested with openpyxl 2.3.4, Python 2.7, Windows

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('openpyxl')
