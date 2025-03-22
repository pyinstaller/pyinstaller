#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Test that the Python's `site` module is disabled and Python is not searching for any user-specific site directories;
# in frozen application, this is effectively checking that PyInstaller's bootloader sets the `site_import` flag in the
# `PyConfig` structure is set to 0 (equivalent of passing -S to python interpreter executable).

import sys

# With `python -S` option (and equivalent `PyConfig.site_import = 0`) set, Python should not import `site` module on
# the startup. Therefore, check that is not imported yet.
#
# NOTE: in the frozen application, the module might end up imported as a dependency of another module that is imported
# when PyInstaller's run-time hooks are imported. If the frozen test script fails at this point, it is best to check
# what run-time hooks were ran, and what imports were made from them; this test script is very simple, so it should
# not warrant imports of many modules with run-time hooks. However, a package like `setuptools` might end up being
# pulled in, for example, via reference to `distutils` (for which it provides replacement).
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
    if site.USER_BASE in sys.path:
        raise SystemExit('USER_BASE found in sys.path!')
