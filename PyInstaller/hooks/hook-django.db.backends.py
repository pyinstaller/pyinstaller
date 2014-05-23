#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import glob

def hook(mod):
    global hiddenimports

    modpath = mod.__path__[0]
    hiddenimports = []

    for fn in glob.glob(os.path.join(modpath, '*')):
        if os.path.isdir(fn):
            fn = os.path.basename(fn)
            hiddenimports.append('django.db.backends.' + fn + '.base')

    # Compiler (see class BaseDatabaseOperations)
    hiddenimports.append("django.db.models.sql.compiler")

    return mod

