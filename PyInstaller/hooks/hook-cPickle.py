#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.compat import is_py2

# copy_reg module name changed in python 3
if is_py2:
    hiddenimports = ['copy_reg', 'types', 'string']
else:
    hiddenimports = ['copyreg', 'types', 'string']
