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

# Since pyi_testmod_path/b lacks an __init__, it's not a module and won't be
# found by modulegraph. So, include its contents in the filesystem.
datas = collect_data_files('pyi_testmod_path', True, 'a')
