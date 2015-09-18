#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Tested with keyring 3.7 on MacOS.

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('keyring.backends')
