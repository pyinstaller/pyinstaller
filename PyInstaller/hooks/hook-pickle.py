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

# Only required when run as `__main__`
excludedimports = ["argparse"]

# pickle also imports `doctest`, which also is only used when run an `__main__`. Anyway, excluding it made some Qt
# related tests fail terribly with "ModuleNotFoundError: No module named '__future__'" when running the executable.
