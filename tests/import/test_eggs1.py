#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# This file is part of the package for testing eggs in `PyInstaller`.


import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'unzipped.egg'))

import pkg_resources

t = pkg_resources.resource_string('unzipped_egg', 'data/datafile.txt')
assert t.rstrip() == 'This is data file for `unzipped`.'

import unzipped_egg
assert unzipped_egg.data == 'This is data file for `unzipped`.'

print('Okay.')
