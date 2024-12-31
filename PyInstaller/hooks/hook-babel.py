#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_data_files

# Ensure that .dat files from locale-data sub-directory are collected.
datas = collect_data_files('babel')

# Unpickling of locale-data/root.dat currently (babel v2.16.0) requires classes from following modules, so ensure that
# they are always collected:
hiddenimports = [
    "babel.dates",
    "babel.localedata",
    "babel.plural",
    "babel.numbers",
]
