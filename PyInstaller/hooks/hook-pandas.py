#-----------------------------------------------------------------------------
# Copyright (c) 2017-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller import compat
from PyInstaller.utils.hooks import collect_submodules, get_installer

from packaging.version import Version

pandas_version = Version(compat.importlib_metadata.version("pandas")).release
pandas_installer = get_installer('pandas')

datas = []
binaries = []

# Pandas keeps Python extensions loaded with dynamic imports here.
hiddenimports = collect_submodules('pandas._libs')

# Pandas 1.2.0 and later require cmath hidden import on linux and macOS. On Windows, this is not strictly required, but
# we add it anyway to keep things simple (and future-proof).
if pandas_version >= (1, 2, 0):
    hiddenimports += ['cmath']

# Pandas 2.1.0 started using `delvewheel` for its Windows PyPI wheels. Ensure that DLLs from `pandas.libs` directory are
# collected regardless of whether binary dependency analysis manages to pick them up or not. See a similar block in the
# `numpy` hook for additional explanation.
if compat.is_win and pandas_version >= (2, 1, 0) and pandas_installer != 'conda':
    from PyInstaller.utils.hooks import collect_delvewheel_libs_directory
    datas, binaries = collect_delvewheel_libs_directory("pandas", datas=datas, binaries=binaries)
