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

from PyInstaller import compat
from PyInstaller.utils.hooks.setuptools import setuptools_info

datas = []

hiddenimports = [
    # Test case import/test_zipimport2 fails during importing pkg_resources or setuptools when module not present.
    'distutils.command.build_ext',
    'setuptools.msvc',
]

# Necessary for setuptools on Mac/Unix
if compat.is_unix or compat.is_darwin:
    hiddenimports.append('syslog')

# Prevent the following modules from being collected solely due to reference from anywhere within setuptools (or
# its vendored dependencies).
excludedimports = [
    'pytest',
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
#
# NOTE: with setuptools >= 71.0, we do not need to add modules from `setuptools._vendored` to hidden imports anymore,
# because the aliases we set up should ensure that the necessary parts get collected. We still need them for earlier
# versions of setuptools, though.
if setuptools_info.version < (71, 0):
    hiddenimports += setuptools_info.vendored_modules

# The situation with vendored distutils (from `setuptools._distutils`) is a bit more complicated; python >= 3.12 does
# not provide stdlib version of `distutils` anymore, so our corresponding pre-safe-import-module hook sets up aliases.
# In earlier python versions, stdlib version is available as well, and at run-time, we might need both versions present,
# so that whichever is applicable can be used. Therefore, for python < 3.12, we need to add the vendored distuils
# modules to hidden imports.
if setuptools_info.distutils_vendored and not compat.is_py312:
    hiddenimports += setuptools_info.distutils_modules

# With setuptools >= 71.0.0, the vendored packages also have metadata, and might also contain data files that need to
# be collected. The list of corresponding data files is kept cached in `setuptools_info.vendored_data` (to minimize the
# number of times we need to call collect_data_files()).
#
# While it might be tempting to simply collect all data files and be done with it, we actually need to match the
# collection behavior for the stand-alone versions of these packages; i.e., we should collect metadata (and/or data
# files) for the vendored package only if the same data is also collected for stand-alone version. Otherwise, we risk
# inconsistent behavior and potential mismatches; for example, if we collected metadata for vendored package A here,
# but end up collecting stand-alone A, for which we normally do not collect the metadata, then at run-time, we will end
# up with stand-alone copy of A and vendored copy of its metadata being discoverable.
#
# Therefore, if metadata and/or metadata needs to be collected, do it in corresponding sub-package hook (for an example,
# see `hook-setuptools._vendor.jaraco.text.py`).
