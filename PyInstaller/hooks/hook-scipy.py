# -----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

import glob
import os
import sysconfig

from PyInstaller.compat import is_win, is_linux
from PyInstaller.utils.hooks import (
    get_module_file_attribute,
    check_requirement,
    collect_delvewheel_libs_directory,
    collect_submodules,
)

binaries = []
datas = []

# Package the DLL bundle that official scipy wheels for Windows ship The DLL bundle will either be in extra-dll on
# windows proper and in .libs if installed on a virtualenv created from MinGW (Git-Bash for example)
if is_win:
    extra_dll_locations = ['extra-dll', '.libs']
    for location in extra_dll_locations:
        dll_glob = os.path.join(os.path.dirname(get_module_file_attribute('scipy')), location, "*.dll")
        if glob.glob(dll_glob):
            binaries.append((dll_glob, "."))

# Handle delvewheel-enabled win32 wheels, which have external scipy.libs directory (scipy >= 0.9.2)
if check_requirement("scipy >= 1.9.2") and is_win:
    datas, binaries = collect_delvewheel_libs_directory('scipy', datas=datas, binaries=binaries)

# collect library-wide utility extension modules
hiddenimports = ['scipy._lib.%s' % m for m in ['messagestream', "_ccallback_c", "_fpumode"]]

# In scipy 1.14.0, `scipy._lib.array_api_compat.numpy` added a programmatic import of its `.fft` submodule, which needs
# to be added to hiddenimports.
if check_requirement("scipy >= 1.14.0"):
    hiddenimports += ['scipy._lib.array_api_compat.numpy.fft']

# If scipy is provided by Debian's python3-scipy, its scipy.__config__ submodule is renamed to a dynamically imported
# scipy.__config__${SOABI}__
# https://salsa.debian.org/python-team/packages/scipy/-/blob/1255922cf7c52b05aa44fb733449953cd9adb815/debian/patches/scipy_config_SOABI.patch
if is_linux and "dist-packages" in get_module_file_attribute("scipy"):
    hiddenimports.append('scipy.__config__' + sysconfig.get_config_var('SOABI') + '__')

# The `scipy._lib.array_api_compat.numpy` module performs a `from numpy import *`; in numpy 2.0.0, `numpy.f2py` was
# added to `numpy.__all__` attribute, but at the same time, the upstream numpy hook adds `numpy.f2py` to
# `excludedimports`. Therefore, the `numpy.f2py` sub-package ends up missing. Due to the way exclusion mechanism works,
# we need to add both `numpy.f2py` and all its submodules to hiddenimports here.
if check_requirement("numpy >= 2.0.0"):
    hiddenimports += collect_submodules('numpy.f2py', filter=lambda name: name != 'numpy.f2py.tests')
