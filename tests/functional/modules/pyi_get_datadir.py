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

# This module assists in determining the location of the tests/functional/data directory.

import sys
import os.path

from pyi_testmod_gettemp import gettemp


# This function returns the location of the tests/functional/data directory when run from a test,
# either built by Pyinstaller or simply run from the Python interpreter.
def get_data_dir():
    # Some tests need input files to operate on. There are two cases:
    if getattr(sys, 'frozen', False):
        # 1. Frozen: rely on gettemp to find the correct directory both in onefile and in onedir modes.
        return gettemp('data')
    else:
        # 2. Not frozen: rely on the filesystem layout of this git repository.
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
