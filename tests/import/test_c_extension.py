#
# Copyright (C) 2012, Martin Zibricky
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


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
