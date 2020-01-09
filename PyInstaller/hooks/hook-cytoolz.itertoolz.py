#-----------------------------------------------------------------------------
# Copyright (c) 2018-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Hook for the cytoolz package: https://pypi.python.org/pypi/cytoolz
# Tested with cytoolz 0.9.0 and Python 3.5.2, on Ubuntu Linux x64

hiddenimports = [ 'cytoolz.utils', 'cytoolz._signatures' ]
