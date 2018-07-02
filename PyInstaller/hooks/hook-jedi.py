#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for Jedi, a static analysis tool https://pypi.org/project/jedi/

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('jedi')
