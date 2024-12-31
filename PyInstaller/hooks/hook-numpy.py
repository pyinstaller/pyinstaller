#-----------------------------------------------------------------------------
# Copyright (c) 2013-2024, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader. Additional
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# --- Copyright Disclaimer ---
#
# An earlier copy of this hook has been submitted to the NumPy project, where it was integrated in v1.23.0rc1
# (https://github.com/numpy/numpy/pull/20745), under terms and conditions outlined in their repository [1].
#
# A special provision is hereby granted to the NumPy project that allows the NumPy copy of the hook to incorporate the
# changes made to this (PyInstaller's) copy of the hook, subject to their licensing terms as opposed to PyInstaller's
# (stricter) licensing terms.
#
# .. refs:
#
#   [1] NumPy's license: https://github.com/numpy/numpy/blob/master/LICENSE.txt

# NOTE: when comparing the contents of this hook and the NumPy version of the hook (for example, to port changes), keep
# in mind that this copy is PyInstaller-centric - it caters to the version of PyInstaller it is bundled with, but needs
# to account for different behavior of different NumPy versions. In contrast, the NumPy copy of the hook caters to the
# version of NumPy it is bundled with, but should account for behavior differences in different PyInstaller versions.

# Override the default hook priority so that our copy of hook is used instead of NumPy's one (which has priority 0,
# the default for upstream hooks).
# $PyInstaller-Hook-Priority: 1

from PyInstaller import compat
from PyInstaller.utils.hooks import (
    get_installer,
    collect_dynamic_libs,
)

from packaging.version import Version

numpy_version = Version(compat.importlib_metadata.version("numpy")).release
numpy_installer = get_installer('numpy')

hiddenimports = []
datas = []
binaries = []

# Collect shared libraries that are bundled inside the numpy's package directory. With PyInstaller 6.x, the directory
# layout of collected shared libraries should be preserved (to match behavior of the binary dependency analysis). In
# earlier versions of PyInstaller, it was necessary to collect the shared libraries into application's top-level
# directory (because that was also what binary dependency analysis in PyInstaller < 6.0 did).
binaries += collect_dynamic_libs("numpy")

# Check if we are using Anaconda-packaged numpy
if numpy_installer == 'conda':
    # Collect DLLs for NumPy and its dependencies (MKL, OpenBlas, OpenMP, etc.) from the communal Conda bin directory.
    from PyInstaller.utils.hooks import conda_support
    datas += conda_support.collect_dynamic_libs("numpy", dependencies=True)

# NumPy 1.26 started using `delvewheel` for its Windows PyPI wheels. While contemporary PyInstaller versions
# automatically pick up DLLs from external `numpy.libs` directory, this does not work on Anaconda python 3.8 and 3.9
# due to defunct `os.add_dll_directory`, which forces `delvewheel` to use the old load-order file approach. So we need
# to explicitly ensure that load-order file as well as DLLs are collected.
if compat.is_win and numpy_version >= (1, 26) and numpy_installer == 'pip':
    from PyInstaller.utils.hooks import collect_delvewheel_libs_directory
    datas, binaries = collect_delvewheel_libs_directory("numpy", datas=datas, binaries=binaries)

# Submodules PyInstaller cannot detect (probably because they are only imported by extension modules, which PyInstaller
# cannot read).
if numpy_version >= (2, 0):
    # In v2.0.0, `numpy.core` was renamed to `numpy._core`.
    # See https://github.com/numpy/numpy/commit/47b70cbffd672849a5d3b9b6fa6e515700460fd0
    hiddenimports += ['numpy._core._dtype_ctypes', 'numpy._core._multiarray_tests']
else:
    hiddenimports += ['numpy.core._dtype_ctypes']

    # See https://github.com/numpy/numpy/commit/99104bd2d0557078d7ea9a590129c87dd63df623
    if numpy_version >= (1, 25):
        hiddenimports += ['numpy.core._multiarray_tests']

# This hidden import was removed from NumPy hook in v1.25.0 (https://github.com/numpy/numpy/pull/22666). According to
# comment in the linked PR, it should have been unnecessary since v1.19.
if compat.is_conda and numpy_version < (1, 19):
    hiddenimports += ["six"]

# Remove testing and building code and packages that are referenced throughout NumPy but are not really dependencies.
excludedimports = [
    "scipy",
    "pytest",
    "nose",
    "f2py",
    "setuptools",
]

# As of v1.22.0, numpy.testing (imported for example by some scipy modules) requires numpy.distutils and distutils.
# This was due to numpy.testing adding import of numpy.testing._private.extbuild, which in turn imported numpy.distutils
# and distutils. These imports were moved into functions that require them in v1.22.2 and v.1.23.0.
# See: https://github.com/numpy/numpy/pull/20831 and https://github.com/numpy/numpy/pull/20906
# So we can exclude them for all numpy versions except for v1.22.0 and v1.22.1 - the main motivation is to avoid pulling
# in `setuptools` (which nowadays provides its vendored version of `distutils`).
if numpy_version < (1, 22, 0) or numpy_version > (1, 22, 1):
    excludedimports += [
        "distutils",
        "numpy.distutils",
    ]

# In numpy v2.0.0, numpy.f2py submodule has been added to numpy's `__all__` attribute. Therefore, using
# `from numpy import *` leads to an error if `numpy.f2py` is excluded (seen in scipy 1.14). The exclusion in earlier
# releases was not reported to cause any issues, so keep it around. Although it should be noted that it does break an
# explicit import (i.e., ˙import numpy.f2py`) from user's code as well, because it prevents collection of other
# submodules from `numpy.f2py`.
if numpy_version < (2, 0):
    excludedimports += [
        "numpy.f2py",
    ]
