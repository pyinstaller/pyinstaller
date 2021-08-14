#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

name = 'pyi_testmod_relimp.pyi_testmod_relimp.relimp2'

from . import relimp3  # noqa: E402
assert relimp3.name == 'pyi_testmod_relimp.pyi_testmod_relimp.relimp3'

from .. import pyi_testmod_relimp  # noqa: E402
assert pyi_testmod_relimp.name == 'pyi_testmod_relimp.pyi_testmod_relimp'

import pyi_testmod_relimp  # noqa: E402
assert pyi_testmod_relimp.name == 'pyi_testmod_relimp'

import pyi_testmod_relimp.relimp2  # noqa: E402
assert pyi_testmod_relimp.relimp2.name == 'pyi_testmod_relimp.relimp2'

# While this seems to work when running Python, it is wrong:
#  .pyi_testmod_relimp should be a sibling of this package
#from .pyi_testmod_relimp import relimp2  # noqa: E402
#assert pyi_testmod_relimp2.name == 'pyi_testmod_relimp.relimp2'
