#-----------------------------------------------------------------------------
# Copyright (c) 2005-2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Test that the Pythons 'site' module is disabled and Python is not searching for any user-specific site directories.

# Check that option -S is passed to Python interpreter and that sys.path has not been modified.

import sys

# The option -S tells Python not to import `site` on startup. If the site module has already been imported,
# abort the test immediately.
if 'site' in sys.modules:
    raise SystemExit('site module already imported')

import site

# Check that it really is disabled.
if not sys.flags.no_site:
    raise SystemExit('site module is enabled!')

# Default values of attributes from 'site' module when it is disabled.
# Under python 3, ENABLE_USER_SITE should be None.
if site.ENABLE_USER_SITE is not None:
    raise SystemExit(f'ENABLE_USER_SITE is {site.ENABLE_USER_SITE}, expected None!')

# Since we import `site` here in the test, this causes USER_SITE and USER_BASE to be initialized on Py2,
# so all we can do is confirm that the paths aren't in sys.path
if site.USER_SITE is not None:
    if site.USER_SITE in sys.path:
        raise SystemExit('USER_SITE found in sys.path!')

# This should never happen, USER_BASE is not a site-modules folder and is only used by distutils
# for installing module datas.
if site.USER_BASE is not None:
    if site.USER_SITE in sys.path:
        raise SystemExit('USER_BASE found in sys.path!')
