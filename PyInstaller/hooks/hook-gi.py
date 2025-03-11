#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller import compat
from packaging.version import Version

pygobject_version = Version(compat.importlib_metadata.version("pygobject")).release

hiddenimports = ['gi._error', 'gi._option']

# PyGObject 3.50.0 added support for `asyncio`, and attempts to import inside the `_gi` extension.
if pygobject_version >= (3, 50, 0):
    hiddenimports += ['asyncio']

# PyGobject 3.52.0 added `gi._enum`, which needs to be added to hiddenimports due to being imported from the
# `_gi` extension.
if pygobject_version >= (3, 52, 0):
    hiddenimports += ['gi._enum']
