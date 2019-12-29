# -----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------
import os
import glob
from PyInstaller.compat import is_win
from PyInstaller.utils.hooks import get_module_file_attribute

# if we bundle the testing module, this will cause
# `scipy` to be pulled in unintentionally but numpy imports
# numpy.testing at the top level for historical reasons.
# excludedimports = collect_submodules('numpy.testing')

binaries = []

# package the DLL bundle that official numpy wheels for Windows ship
# The DLL bundle will either be in extra-dll on windows proper
# and in .libs if installed on a virtualenv created from MinGW (Git-Bash
# for example)
if is_win:
    extra_dll_locations = ['extra-dll', '.libs']
    for location in extra_dll_locations:
        dll_glob = os.path.join(os.path.dirname(
            get_module_file_attribute('numpy')), location, "*.dll")
        if glob.glob(dll_glob):
            binaries.append((dll_glob, "."))
