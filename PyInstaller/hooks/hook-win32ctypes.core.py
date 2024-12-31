#-----------------------------------------------------------------------------
# Copyright (c) 2020-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# TODO: remove this hook during PyInstaller 4.5 release cycle!

from PyInstaller.utils.hooks import can_import_module, collect_submodules

# We need to collect submodules from win32ctypes.core.cffi or win32ctypes.core.ctypes for win32ctypes.core to work.
# Always collect the `ctypes` backend, and add the `cffi` one if `cffi` is available. Having the `ctypes` backend always
# available helps in situations when `cffi` is available in the build environment, but is disabled at run-time or not
# collected (e.g., due to `--exclude cffi`).
hiddenimports = collect_submodules('win32ctypes.core.ctypes')
if can_import_module('cffi'):
    hiddenimports += collect_submodules('win32ctypes.core.cffi')
