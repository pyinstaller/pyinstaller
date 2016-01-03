#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


name = 'pyi_testmod_relimp.pyi_testmod_relimp.relimp2'

from . import relimp3
assert relimp3.name == 'pyi_testmod_relimp.pyi_testmod_relimp.relimp3'

from .. import pyi_testmod_relimp
assert pyi_testmod_relimp.name == 'pyi_testmod_relimp.pyi_testmod_relimp'

import pyi_testmod_relimp
assert pyi_testmod_relimp.name == 'pyi_testmod_relimp'

import pyi_testmod_relimp.relimp2
assert pyi_testmod_relimp.relimp2.name == 'pyi_testmod_relimp.relimp2'

# While this seams to work when running Python, it is wrong:
#  .pyi_testmod_relimp should be a sibling of this package
#from .pyi_testmod_relimp import relimp2
#assert pyi_testmod_relimp2.name == 'pyi_testmod_relimp.relimp2'

