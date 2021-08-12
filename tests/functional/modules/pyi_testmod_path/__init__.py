#-----------------------------------------------------------------------------
# Copyright (c) 2015-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
import os.path
# Insert a/ at the beginning of __path__.
__path__.insert(0, os.path.join(__path__[0], 'a'))
# Import b, which should now find a/b.py, no ./b.py.
import b  # noqa: F401, E402
