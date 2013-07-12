#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Test inclusion of fake 'site' module.


import site


# Default values in fake 'site' module should be False, None or empty list.

if not site.ENABLE_USER_SITE == False:
    raise SystemExit('ENABLE_USER_SITE not False.')
if not site.PREFIXES == []:
    raise SystemExit('PREFIXES not empty list.')

if site.USER_SITE is not None and site.USER_BASE is not None:
    raise SystemExit('USER_SITE or USER_BASE not None.')
