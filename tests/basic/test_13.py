#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


print('test13 - Used to fail if _xmlplus is installed')


import sys


if sys.version_info[:2] >= (2, 5):
    import _elementtree
    print('test13 DONE')
else:
    print('Python 2.5 test13 skipped')
