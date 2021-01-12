# -----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------
import os
import glob
from PyInstaller.compat import is_win, is_venv, base_prefix
from PyInstaller.utils.hooks import get_module_file_attribute

# numpy.testing is unconditionally imported by numpy, thus we can not exclude
# .testing (which would be preferred). Anyway, this only saves about 7
# modules. See also https://github.com/numpy/numpy/issues/17183
#excludedimports = ["numpy.testing"]

# FIXME check if this workaround is still necessary!
if is_win:
    from PyInstaller.utils.win32.winutils import extend_system_path
    from distutils.sysconfig import get_python_lib
    # SciPy/Numpy Windows builds from http://www.lfd.uci.edu/~gohlke/pythonlibs
    # contain some dlls in directory like C:\Python27\Lib\site-packages\numpy\core\
    numpy_core_paths = [os.path.join(get_python_lib(), 'numpy', 'core')]
    # In virtualenv numpy might be installed directly in real prefix path.
    # Then include this path too.
    if is_venv:
        numpy_core_paths.append(
            os.path.join(base_prefix, 'Lib', 'site-packages', 'numpy', 'core')
        )
    extend_system_path(numpy_core_paths)
    del numpy_core_paths

# if we bundle the testing module, this will cause
# `scipy` to be pulled in unintentionally but numpy imports
# numpy.testing at the top level for historical reasons.
# excludedimports = collect_submodules('numpy.testing')

binaries = []

# package the DLL bundle that official numpy wheels for Windows ship
# The DLL bundle will either be in extra-dll on windows proper
# and in .libs if installed on a virtualenv created from MinGW (Git-Bash
# for example)
if is_win:
    extra_dll_locations = ['extra-dll', '.libs']
    for location in extra_dll_locations:
        dll_glob = os.path.join(os.path.dirname(
            get_module_file_attribute('numpy')), location, "*.dll")
        if glob.glob(dll_glob):
            binaries.append((dll_glob, "."))
