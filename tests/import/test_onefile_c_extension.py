#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# In dist directory are Python C-extension file names like module.submodule.so
# E.g.  ./simplejson/_speedups.so  ->  ./simplejson._speedups.so


import os
import sys


from simplejson import _speedups


modpath = os.path.join(sys.prefix, 'simplejson._speedups')
frozen_modpath = os.path.splitext(_speedups.__file__)[0]


print('Module path expected: ' + modpath)
print('Module path  current: ' + frozen_modpath)


if not frozen_modpath == modpath:
    raise SystemExit('Python C-extension file name is not correct.')
