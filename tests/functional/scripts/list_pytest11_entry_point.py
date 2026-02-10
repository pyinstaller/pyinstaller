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
"""
Print all modules exporting the entry point 'pytest11'.
"""

import sys

# entry_points() with group keyword argument is available in stdlib's importlib.metadata starting with python 3.10; on
# older versions we require importlib-metadata backport (which should be available and of sufficient version due to
# being part of PyInstaller's requirements).
if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

plugins = sorted(i.module for i in importlib_metadata.entry_points(group="pytest11"))

print("\n".join(plugins))
