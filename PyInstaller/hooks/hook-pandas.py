#-----------------------------------------------------------------------------
# Copyright (c) 2017-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_submodules

# Pandas keeps Python extensions loaded with dynamic imports here.
hiddenimports = collect_submodules('pandas._libs')
