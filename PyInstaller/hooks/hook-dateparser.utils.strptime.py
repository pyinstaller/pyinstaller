#-----------------------------------------------------------------------------
# Copyright (c) 2018-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for dateparser: https://pypi.org/project/dateparser/

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ["_strptime"] + collect_submodules('dateparser.data')
