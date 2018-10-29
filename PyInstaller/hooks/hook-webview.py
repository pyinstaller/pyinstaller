#-----------------------------------------------------------------------------
# Copyright (c) 2018-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
pywebview requires WebBrowserInterop dll on Windows
"""

import platform
import ctypes
from os.path import join, exists

from PyInstaller.compat import is_win, getsitepackages

if is_win:
    if platform.architecture()[0] == '64bit':
        dll_name = 'WebBrowserInterop.x64.dll'
    else:
        dll_name = 'WebBrowserInterop.x86.dll'

    library = ctypes.util.find_library(dll_name)
    datas = []
    if library:
        datas = [(library, '.')]
    else:
        for sitepack in getsitepackages():
            library = join(sitepack, 'lib', dll_name)
            if exists(library):
                datas = [(library, '.')]
        if not datas:
            raise Exception(dll_name + ' not found')
