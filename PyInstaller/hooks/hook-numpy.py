# -----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
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
if is_win:
    dll_glob = os.path.join(os.path.dirname(
        get_module_file_attribute('numpy')), 'extra-dll', "*.dll")
    if glob.glob(dll_glob):
        binaries.append((dll_glob, "."))
