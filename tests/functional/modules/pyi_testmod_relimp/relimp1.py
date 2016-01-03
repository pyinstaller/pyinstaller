#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


name = 'pyi_testmod_relimp.relimp1'

from . import relimp2 as upper
from . pyi_testmod_relimp import relimp2 as lower

assert upper.name == 'pyi_testmod_relimp.relimp2'
assert lower.name == 'pyi_testmod_relimp.pyi_testmod_relimp.relimp2'

if upper.__name__ == lower.__name__:
    raise SystemExit("Imported the same module")

if upper.__file__ == lower.__file__:
    raise SystemExit("Imported the same file")
