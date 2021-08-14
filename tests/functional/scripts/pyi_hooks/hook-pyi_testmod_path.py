#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
from PyInstaller.utils.hooks import collect_data_files

# Since pyi_testmod_path/a lacks an __init__, it is not a regular package and its contents will not be
# found by modulegraph. So, collect its contents manually, and ensure they end up on filesystem.
datas = collect_data_files('pyi_testmod_path', True, 'a')
