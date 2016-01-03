#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


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
print(('Actual   mod.__file__: %s' % module.__file__))
print(('Expected mod.__file__: %s' % correct_mod))
print(('Actual   pkg.__file__: %s' % package.__file__))
print(('Expected pkg.__file__: %s' % correct_pkg))


# Test correct values.
if not module.__file__ == correct_mod:
    raise SystemExit('MODULE.__file__ attribute is wrong.')
if not package.__file__ == correct_pkg:
    raise SystemExit('PACKAGE.__file__ attribute is wrong.')
