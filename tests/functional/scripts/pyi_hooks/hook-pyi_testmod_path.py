#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
from PyInstaller.utils.hooks import collect_data_files

# Since pyi_testmod_path/b lacks an __init__, it's not a module and won't be
# found by modulegraph. So, include its contents in the filesystem.
datas = collect_data_files('pyi_testmod_path', True, 'a')
