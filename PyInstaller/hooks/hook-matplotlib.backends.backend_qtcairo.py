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

# This module conditionally imports PyQt6:
# https://github.com/matplotlib/matplotlib/blob/9e18a343fb58a2978a8e27df03190ed21c61c343/lib/matplotlib/backends/backend_qtcairo.py#L24-L25
# Suppress this import to prevent PyQt6 from being accidentally pulled in; the actually relevant Qt bindings are
# determined by our hook for `matplotlib.backends.qt_compat` module.
excludedimports = ['PyQt6']
