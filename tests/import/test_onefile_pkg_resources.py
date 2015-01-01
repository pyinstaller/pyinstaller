#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# With module 'pkg_resources' it should not matter if a file is stored
# on file system, in zip archive or bundled with frozen app.
import pkg_resources as res
import pkg3

# With frozen app the resources is available in directory
# os.path.join(sys._MEIPASS, 'pkg3/sample-data.txt')
data = res.resource_string(pkg3.__name__, 'sample-data.txt')
if data:
    data = data.strip()

if data != 'This is data text for testing the packaging module data.':
    raise SystemExit('Error: Could not read data with pkg_resources module.')
print 'Okay: Resource data read.'
