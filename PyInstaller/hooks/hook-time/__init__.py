#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Since Python 2.3, builtin module "time" imports Python module _strptime
# to implement "time.strptime".
hiddenimports = ['_strptime']
