#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

name = 'pyi_testmod_relimp.B.C'

# Import pyi_testmod_relimp.B.D
from . import D  # noqa: E402
# Import pyi_testmod_relimp.B.D.X
from .D import X  # noqa: E402, F401
# Import pyi_testmod_relimp.E
from .. import E  # noqa: E402
# Import pyi_testmod_relimp.F.G
from ..F import G  # noqa: E402
# Import pyi_testmod_relimp.F.H
from ..F import H  # noqa: E402

assert D.name == 'pyi_testmod_relimp.B.D'
assert E.name == 'pyi_testmod_relimp.E'
assert G.name == 'pyi_testmod_relimp.F.G'
assert H.name == 'pyi_testmod_relimp.F.H'
