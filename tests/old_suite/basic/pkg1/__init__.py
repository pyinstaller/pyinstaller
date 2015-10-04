#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


""" pkg1 replaces itself with pkg2"""


__all__ = ["a", "b"]
import pkg2
import sys
sys.modules[__name__] = pkg2
from pkg2 import *
