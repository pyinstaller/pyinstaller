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

from PyInstaller.utils.hooks import qt as qtutils

# This module conditionally imports all Qt bindings. Prevent all available bindings from being pulled in by trying to
# select the most applicable one.
#
# The preference order for this module appears to be: PyQt6, PySide6, PyQt5, PySide2 (or just PyQt5, PySide2 if Qt5
# bindings are forced). See:
# https://github.com/matplotlib/matplotlib/blob/9e18a343fb58a2978a8e27df03190ed21c61c343/lib/matplotlib/backends/qt_compat.py#L113-L125
#
# We, however, use the default preference order of the helper function, in order to keep it consistent across multiple
# hooks that use the same helper.
excludedimports = qtutils.exclude_extraneous_qt_bindings(
    hook_name="hook-matplotlib.backends.qt_compat",
    qt_bindings_order=None,
)
