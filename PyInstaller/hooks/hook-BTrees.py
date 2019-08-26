#-----------------------------------------------------------------------------
# Copyright (c) 2015-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for BTrees: https://pypi.org/project/BTrees/4.5.1/

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('BTrees')
