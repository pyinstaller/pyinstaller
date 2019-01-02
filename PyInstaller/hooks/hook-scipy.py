# -----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------

import os
import glob
from PyInstaller.utils.hooks import get_module_file_attribute
from PyInstaller.compat import is_win

binaries = []

# package the DLL bundle that official scipy wheels for Windows ship
if is_win:
    dll_glob = os.path.join(os.path.dirname(
        get_module_file_attribute('scipy')), 'extra-dll', "*.dll")
    if glob.glob(dll_glob):
        binaries.append((dll_glob, "."))

# collect library-wide utility extension modules
hiddenimports = ['scipy._lib.%s' % m for m in [
    'messagestream', "_ccallback_c", "_fpumode"]]
