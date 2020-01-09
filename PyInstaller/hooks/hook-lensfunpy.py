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

from PyInstaller.utils.hooks import collect_data_files
# bundle xml DB files, skip other files (like DLL files on Windows)
datas = list(filter(lambda p: p[0].endswith('.xml'), collect_data_files('lensfunpy')))
hiddenimports = ['numpy', 'enum']
