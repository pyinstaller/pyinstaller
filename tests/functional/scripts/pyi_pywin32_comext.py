#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Test importing modules from win32com that are actually present in
# win32comext, and made available by __path__ changes in win32com.

from win32com.shell import shell
from win32com.propsys import propsys
from win32com.bits import bits
