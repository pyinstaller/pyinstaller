#-----------------------------------------------------------------------------
# Copyright (c) 2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os

from PyInstaller.utils.hooks import get_package_paths
from PyInstaller.utils.hooks import is_module_satisfies
from PyInstaller import compat

# Necessary when using the vectorized subpackage
hiddenimports = ['shapely.prepared']

pkg_base, pkg_dir = get_package_paths('shapely')


binaries = []
if compat.is_win:
    if compat.is_conda:
        lib_dir = os.path.join(compat.base_prefix, 'Library', 'bin')
    else:
        lib_dir = os.path.join(pkg_dir, 'DLLs')
    dll_files = ['geos_c.dll', 'geos.dll']
    binaries += [(os.path.join(lib_dir, f), '.') for f in dll_files]
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
