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


# Test the value of the __file__ module attribute.
# In frozen mode it is for package set to 
# 
#   sys.prefix/package/__init__.pyc
#   sys.prefix/module.pyc


import os
import sys

import shutil as module
import xml.sax as package


correct_mod = os.path.join(sys.prefix, 'shutil.pyc')
correct_pkg = os.path.join(sys.prefix, 'xml', 'sax', '__init__.pyc')


# Print.
print '  mod.__file__: %s' % module.__file__
print '  mod.__file__: %s' % correct_mod
print '  pkg.__file__: %s' % package.__file__
print '  pkg.__file__: %s' % correct_pkg


# Test correct values.
if not module.__file__ == correct_mod:
    raise SystemExit('MODULE.__file__ attribute is wrong.')
if not package.__file__ == correct_pkg:
    raise SystemExit('PACKAGE.__file__ attribute is wrong.')
