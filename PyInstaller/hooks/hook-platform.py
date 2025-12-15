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
import sys

excludedimports = []

# see https://github.com/python/cpython/blob/3.9/Lib/platform.py#L411
# This will exclude `plistlib` for sys.platform != 'darwin'
if sys.platform != 'darwin':
    excludedimports += ["plistlib"]

# Avoid collecting `_ios_support`, which in turn triggers unnecessary collection of `libobjc` shared library if the
# latter happens to be available on the build system.
# See https://github.com/pyinstaller/pyinstaller/issues/9333, as well as
# https://github.com/python/cpython/blob/v3.13.0/Lib/platform.py#L508-L521
# and
# https://github.com/python/cpython/blob/v3.13.0/Lib/_ios_support.py#L13
if sys.platform != 'ios':
    excludedimports += ["_ios_support"]
