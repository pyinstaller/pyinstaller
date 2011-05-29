# -*- mode: python -*-
#!/usr/bin/env python
#
# Copyright (C) 2008 Hartmut Goebel <h.goebel@goebel-consult.de>
# Licence: GNU General Public License version 3 (GPL v3)
#
# This file is part of PyInstaller <http://www.pyinstaller.org>
#
# pyinstaller is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyinstaller is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
"""
test for zipimport - use a more complex import
"""

import os
import sys

print __name__, 'is running'
print 'sys.path:', sys.path
print 'dir contents .exe:', os.listdir(os.path.dirname(sys.executable))
if hasattr(sys, 'frozen') and sys.frozen:
    print '-----------'
    print 'dir contents _MEIPASS2:', os.listdir(os.environ['_MEIPASS2'])

print '-----------'
print 'now importing pkg_resources' 
import pkg_resources

print '-----------'
print 'now importing setuptools.dist'
import setuptools.dist
print '-----------'
print 'now importing setuptools.command'
import setuptools.command
