#-----------------------------------------------------------------------------
# Copyright (c) 2024, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# This module conditionally imports PyQt5:
# https://github.com/pandas-dev/pandas/blob/95308514e1221200e4526dfaf248283f3d7ade06/pandas/io/clipboard/__init__.py#L578-L597
# Suppress this import to prevent PyQt5 from being accidentally pulled in; the actually relevant Qt bindings are
# determined by our hook for `qtpy` module, which contemporary versions of pandas mandate as part of `clipboard` and
# `all` extras:
# https://github.com/pandas-dev/pandas/blob/95308514e1221200e4526dfaf248283f3d7ade06/pyproject.toml#L86
# https://github.com/pandas-dev/pandas/blob/95308514e1221200e4526dfaf248283f3d7ade06/pyproject.toml#L115
excludedimports = ['PyQt5']
