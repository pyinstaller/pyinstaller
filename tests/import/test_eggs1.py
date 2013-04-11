#!/usr/bin/env python
#
# This file is part of the package for testing eggs in `PyInstaller`.
#
# Author:    Hartmut Goebel <h.goebel@goebel-consult.de>
# Copyright: 2012 by Hartmut Goebel
# Licence:   GNU Public Licence v3 (GPLv3)
#

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'unzipped.egg'))

import pkg_resources

t = pkg_resources.resource_string('unzipped_egg', 'data/datafile.txt')
assert t.rstrip() == 'This is data file for `unzipped`.'

import unzipped_egg
assert unzipped_egg.data == 'This is data file for `unzipped`.'

print 'Okay.'
