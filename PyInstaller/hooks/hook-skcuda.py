#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

#hook for skcuda (scikit-cuda)

from PyInstaller.utils.hooks import copy_metadata

datas = collect_all('scikit-cuda')