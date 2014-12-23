#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import pkgutil

data = pkgutil.get_data('__main__', 'pkg3/sample-data.txt')
if data:
    data = data.strip()

if data != 'This is data text for testing the packaging module data.':
    raise SystemExit('Error: Could not read data with pkgutil.get_data().')
print 'Okay: Resource data read.'
