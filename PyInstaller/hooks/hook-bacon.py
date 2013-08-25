from PyInstaller.compat import is_win, is_darwin
from PyInstaller.hooks.hookutils import get_package_paths

import os
import sys
import ctypes

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
        datas = collect_native_files('bacon.windows32', files)
    else:
        datas = collect_native_files('bacon.windows64', files)
elif is_darwin:
    if ctypes.sizeof(ctypes.c_void_p) == 4:
        files = ['Bacon.dylib']
        datas = collect_native_files('bacon.darwin32', files)
    else:
        files = ['Bacon64.dylib']
        datas = collect_native_files('bacon.darwin64', files)
