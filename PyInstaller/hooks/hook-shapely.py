#-----------------------------------------------------------------------------
# Copyright (c) 2017-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os
from ctypes.util import find_library

from PyInstaller.utils.hooks import get_package_paths
from PyInstaller.utils.hooks import is_module_satisfies
from PyInstaller import compat

# Necessary when using the vectorized subpackage
hiddenimports = ['shapely.prepared']

pkg_base, pkg_dir = get_package_paths('shapely')


binaries = []
if compat.is_win:
    # Search conda directory if conda is active, then search standard
    # directory. This is the same order of precidence used in shapely.
    standard_path = os.path.join(pkg_dir, 'DLLs')
    lib_paths = [standard_path, os.environ['PATH']]
    if compat.is_conda:
        conda_path = os.path.join(compat.base_prefix, 'Library', 'bin')
        lib_paths.insert(0, conda_path)
    original_path = os.environ['PATH']
    try:
        os.environ['PATH'] = os.pathsep.join(lib_paths)
        dll_path = find_library('geos_c')
    finally:
        os.environ['PATH'] = original_path
    if dll_path is None:
        raise SystemExit(
            "Error: geos_c.dll not found, required by hook-shapely.py.\n"
            "Please check your installation or provide a pull request to "
            "PyInstaller to update hook-shapely.py.")
    binaries += [(dll_path, '.')]
elif compat.is_linux:
    lib_dir = os.path.join(pkg_dir, '.libs')
    dest_dir = os.path.join('shapely', '.libs')

    # This duplicates the libgeos*.so* files in the build.  PyInstaller will
    # copy them into the root of the build by default, but shapely cannot load
    # them from there in linux IF shapely was installed via a whl file. The
    # whl bundles its' own libgeos with a different name, something like
    # libgeos_c-*.so.* but shapely tries to load libgeos_c.so if there isn't a
    # ./libs directory under its' package. There is a proposed fix for this in
    # shapely but it has not been accepted it:
    # https://github.com/Toblerity/Shapely/pull/485
    if is_module_satisfies('shapely <= 1.6'):
        binaries += [(os.path.join(lib_dir, f), dest_dir) for f in os.listdir(lib_dir)]
