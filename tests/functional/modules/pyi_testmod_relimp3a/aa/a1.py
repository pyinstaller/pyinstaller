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

# NOTE: relative imports do not work beyond toplevel package.

# Should look for module 'pyi_testmod_relimp3c' in current directory.
from .pyi_testmod_relimp3c import c1
# Should look for module 'b1' in directory '../pyi_testmod_relimp3b' - one level up.
from ..pyi_testmod_relimp3b import b1


def getString():
    return b1.string + c1.string
