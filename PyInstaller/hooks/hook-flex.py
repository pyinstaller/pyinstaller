#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# hook for https://github.com/pipermerriam/flex

from PyInstaller.utils.hooks import copy_metadata

datas = copy_metadata('flex')
