#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# In dist directory are Python C-extension file names, e.g., module.submodule.so
# For example: ./simplejson/_speedups.so -> ./simplejson._speedups.so

import os
import sys

# List of suffixes for Python C extension modules.
from importlib.machinery import EXTENSION_SUFFIXES

from simplejson import _speedups

modpath = os.path.join(sys.prefix, 'simplejson._speedups')
frozen_modpath = _speedups.__file__

print('Module path expected:', modpath, '+ ext', file=sys.stderr)
print('Module path  current:', frozen_modpath, file=sys.stderr)

# Filename extensions can include several dots (e.g., '.cpython-33m.so'), so we cannot simply use os.path.splitext(),
# but have to loop over all possible extensions.
for ext in EXTENSION_SUFFIXES:
    if modpath + ext == frozen_modpath:
        print('             matched:', modpath + ext, file=sys.stderr)
        break
else:
    if not getattr(sys, 'frozen', False):
        raise SystemExit('This script only works corretly when frozen')
    raise SystemExit('Python C-extension file name is not correct.')
