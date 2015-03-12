#-----------------------------------------------------------------------------
# Copyright (c) 2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Hook for the bcrypt module.
"""

import os.path
import site
import glob
from PyInstaller.hooks.hookutils import PY_EXTENSION_SUFFIXES

def hook(mod):
    """
    Include the bcrypt extension from the site-packages folder.
    These need to be placed in the main package folder.
    """
    lib_paths = site.getsitepackages()
    for lib_path in lib_paths:
        for ext in PY_EXTENSION_SUFFIXES:
            ffimods = glob.glob(os.path.join(lib_path, '*_cffi_*%s*' % ext))
            for f in ffimods:
                name = os.path.basename(f)
                # TODO fix this hook to use attribute 'binaries'.
                mod.pyinstaller_binaries.append((name, f, 'BINARY'))
    return mod
