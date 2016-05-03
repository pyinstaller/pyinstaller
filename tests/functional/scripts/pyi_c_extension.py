#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from __future__ import print_function

# In dist directory are Python C-extension file names like module.submodule.so
# E.g.  ./simplejson/_speedups.so  ->  ./simplejson._speedups.so

import os
import sys

# List of suffixes for Python C extension modules.
try:
    # In Python 3.3+ There is a list
    from importlib.machinery import EXTENSION_SUFFIXES
except ImportError:
    # Python 2 does not have this
    import imp
    EXTENSION_SUFFIXES = [f[0] for f in imp.get_suffixes()
                          if f[2] == imp.C_EXTENSION]

from simplejson import _speedups

modpath = os.path.join(sys.prefix, 'simplejson._speedups')
frozen_modpath = _speedups.__file__

print('Module path expected:', modpath, '+ ext', file=sys.stderr)
print('Module path  current:', frozen_modpath, file=sys.stderr)

# In Python3, filename extensions can include several dots (e.g.
# '.cpython-33m.so'), so we can not simply use os.path.splitext(), but
# have to loop over all possible extensions.
for ext in EXTENSION_SUFFIXES:
    if modpath + ext == frozen_modpath:
        print('             matched:', modpath + ext, file=sys.stderr)
        break
else:
    if not getattr(sys, 'frozen', False):
        raise SystemExit('This script only works corretly when frozen')
    raise SystemExit('Python C-extension file name is not correct.')
