#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Test for zipimport - use a more complex import


import os
import sys

print __name__, 'is running'
print 'sys.path:', sys.path
print 'dir contents .exe:', os.listdir(os.path.dirname(sys.executable))
if hasattr(sys, 'frozen') and sys.frozen:
    print '-----------'
    print 'dir contents sys._MEIPASS:', os.listdir(sys._MEIPASS)

print '-----------'
print 'now importing pkg_resources' 
import pkg_resources

print '-----------'
print 'now importing setuptools.dist'
import setuptools.dist
print '-----------'
print 'now importing setuptools.command'
