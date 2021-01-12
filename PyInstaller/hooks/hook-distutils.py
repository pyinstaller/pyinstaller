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

"""
`distutils`-specific post-import hook.

This hook freezes the external `Makefile` and `pyconfig.h` files bundled with
the active Python interpreter, which the `distutils.sysconfig` module parses at
runtime for platform-specific metadata.
"""

# TODO Verify that bundling Makefile and pyconfig.h is still required for Python 3.

import os
import sysconfig

from PyInstaller.utils.hooks import relpath_to_config_or_make

_CONFIG_H = sysconfig.get_config_h_filename()
_MAKEFILE = sysconfig.get_makefile_filename()

# Data files in PyInstaller hook format.
datas = [(_CONFIG_H, relpath_to_config_or_make(_CONFIG_H))]

# The Makefile does not exist on all platforms, eg. on Windows
if os.path.exists(_MAKEFILE):
    datas.append((_MAKEFILE, relpath_to_config_or_make(_MAKEFILE)))
