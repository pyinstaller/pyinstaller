#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys

def hook(mod):
    if 'posix' in sys.builtin_module_names:
        removes = ['nt', 'ntpath', 'dos', 'dospath', 'os2', 'mac', 'macpath',
                   'ce', 'riscos', 'riscospath', 'win32api', 'riscosenviron']
    elif 'nt' in sys.builtin_module_names:
        removes = ['dos', 'dospath', 'os2', 'mac', 'macpath', 'ce', 'riscos',
                   'riscospath', 'riscosenviron',]

    mod.pyinstaller_imports = [m
                   for m in mod.pyinstaller_imports
                   # if first part of module-name not in removes
                   if m[0].split('.', 1)[0] not in removes
    ]
    return mod
