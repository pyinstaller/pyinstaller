#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Test that the Pythons 'site' module is disabled and Python is not searching
# for any user-specific site directories.

# Check that option -S is passed to Python interpreter.


import site
import sys


# Check it is really disabled.
if not sys.flags.no_site:
    raise SystemExit('site module is enabled!')

# Default values 'site' module when it is disabled.
if not site.ENABLE_USER_SITE == None:
    raise SystemExit('ENABLE_USER_SITE not False.')
if site.USER_SITE is not None and site.USER_BASE is not None:
    raise SystemExit('USER_SITE or USER_BASE not None.')
