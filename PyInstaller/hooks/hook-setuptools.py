#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.compat import is_darwin, is_unix
from PyInstaller.utils.hooks.setuptools import setuptools_info

datas = []

hiddenimports = [
    # Test case import/test_zipimport2 fails during importing pkg_resources or setuptools when module not present.
    'distutils.command.build_ext',
    'setuptools.msvc',
]

# Necessary for setuptools on Mac/Unix
if is_unix or is_darwin:
    hiddenimports.append('syslog')

# Prevent the following modules from being collected solely due to reference from anywhere within setuptools (or
# its vendored dependencies).
excludedimports = [
    'pytest',
    'unittest',
    'numpy',  # originally from hook-setuptools.msvc
    'docutils',  # originally from hool-setuptools._distutils.command.check
]

# setuptools >= 39.0.0 is "vendoring" its own direct dependencies from "_vendor" to "extern". This also requires
# 'pre_safe_import_module/hook-setuptools.extern.six.moves.py' to make the moves defined in 'setuptools._vendor.six'
# importable under 'setuptools.extern.six'.
#
# With setuptools 71.0.0, the vendored packages are exposed to the outside world by `setuptools._vendor` location being
# appended to `sys.path`, and the `VendorImporter` is gone (i.e., no more mapping to `setuptools.extern`). Since the
# vendored dependencies are now exposed as top-level modules (provided upstream versions are not available, as they
# would take precedence due to `sys.path` ordering), we need pre-safe-import-module hooks that detect when only vendored
# version is available, and add aliases to prevent duplicated collection. For list of vendored packages for which we
# need such pre-safe-import-module hooks, see the code in `PyInstaller.utils.hooks.setuptools`.
#
# The list of submodules from `setuptools._vendor` is now available in `setuptools_info.vendored_modules` (and covers
# all setuptools versions).
hiddenimports += setuptools_info.vendored_modules

# With setuptools >= 71.0.0, we also need to ensure that metadata of vendored packages as well as their data files are
# collected. The list of corresponding data files is kept in `setuptools_info.vendored_data`. On earlier setuptools
# versions, the list is empty.
datas += setuptools_info.vendored_data

# As of setuptools >= 60.0, we need to collect the vendored version of distutils via hiddenimports. The corresponding
# pyi_rth_setuptools runtime hook ensures that the _distutils_hack is installed at the program startup, which allows
# setuptools to override the stdlib distutils with its vendored version, if necessary.
#
# The list of submodules from `setuptools._distutils` (plus `_distutils_hack˙) is kept in
# `setuptools_info.distutils_modules˙.
if setuptools_info.distutils_vendored:
    hiddenimports += setuptools_info.distutils_modules
