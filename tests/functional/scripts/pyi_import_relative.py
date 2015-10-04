#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import pyi_testmod_relimp.B.C
from pyi_testmod_relimp.F import H
import pyi_testmod_relimp.relimp1


assert pyi_testmod_relimp.relimp1.name == 'pyi_testmod_relimp.relimp1'
assert pyi_testmod_relimp.B.C.name == 'pyi_testmod_relimp.B.C'
assert pyi_testmod_relimp.F.H.name == 'pyi_testmod_relimp.F.H'
