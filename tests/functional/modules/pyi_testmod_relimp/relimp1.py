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

name = 'pyi_testmod_relimp.relimp1'

from . import relimp2 as upper  # noqa: E402
from .pyi_testmod_relimp import relimp2 as lower  # noqa: E402

assert upper.name == 'pyi_testmod_relimp.relimp2'
assert lower.name == 'pyi_testmod_relimp.pyi_testmod_relimp.relimp2'

if upper.__name__ == lower.__name__:
    raise SystemExit("Imported the same module")

if upper.__file__ == lower.__file__:
    raise SystemExit("Imported the same file")
