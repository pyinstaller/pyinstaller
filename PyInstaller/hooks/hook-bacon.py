#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for Bacon (https://github.com/aholkner/bacon)
# Bacon requires its native DLLs to be copied alongside frozen executable.

import os
import ctypes

from PyInstaller.compat import is_win, is_darwin
from PyInstaller.utils.hooks import get_package_paths


def collect_native_files(package, files):
    pkg_base, pkg_dir = get_package_paths(package)
    return [(os.path.join(pkg_dir, file), '') for file in files]

if is_win:
    files = ['Bacon.dll', 
             'd3dcompiler_46.dll',
             'libEGL.dll',
             'libGLESv2.dll',
             'msvcp110.dll',
             'msvcr110.dll',
             'vccorllib110.dll']
    if ctypes.sizeof(ctypes.c_void_p) == 4:
        hiddenimports = ["bacon.windows32"]
        datas = collect_native_files('bacon.windows32', files)
    else:
        hiddenimports = ["bacon.windows64"]
        datas = collect_native_files('bacon.windows64', files)
elif is_darwin:
    if ctypes.sizeof(ctypes.c_void_p) == 4:
        hiddenimports = ["bacon.darwin32"]
        files = ['Bacon.dylib']
        datas = collect_native_files('bacon.darwin32', files)
    else:
        hiddenimports = ["bacon.darwin64"]
        files = ['Bacon64.dylib']
        datas = collect_native_files('bacon.darwin64', files)
