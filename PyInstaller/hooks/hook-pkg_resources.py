#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
from PyInstaller.utils.hooks import collect_submodules

# pkg_resources keeps vendored modules in its _vendor subpackage, and does
# sys.meta_path based import magic to expose them as pkg_resources.extern.*
hiddenimports = collect_submodules('pkg_resources._vendor')

excludedimports = ['__main__']
