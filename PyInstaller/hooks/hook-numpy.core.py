#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
# If numpy is built with MKL support it depends on a set of libraries loaded
# at runtime. Since PyInstaller's static analysis can't find them they must be
# included manually.
#
# See
# https://github.com/pyinstaller/pyinstaller/issues/1881
# https://github.com/pyinstaller/pyinstaller/issues/1969
# for more information
import os
import os.path
import re
from PyInstaller.utils.hooks import get_package_paths
from PyInstaller import log as logging 
from PyInstaller import compat

binaries = []

# look for libraries in numpy package path
pkg_base, pkg_dir = get_package_paths('numpy.core')
re_anylib = re.compile(r'\w+\.(?:dll|so|dylib)', re.IGNORECASE)
dlls_pkg = [f for f in os.listdir(pkg_dir) if re_anylib.match(f)]
binaries += [(os.path.join(pkg_dir, f), '.') for f in dlls_pkg]

# look for MKL libraries in pythons lib directory
# TODO: check numpy.__config__ if numpy is actually depending on MKL
# TODO: determine which directories are searched by the os linker
if compat.is_win:
    lib_dir = os.path.join(compat.base_prefix, "Library", "bin")
else:
    lib_dir = os.path.join(compat.base_prefix, "lib")
if os.path.isdir(lib_dir):
    re_mkllib = re.compile(r'^(?:lib)?mkl\w+\.(?:dll|so|dylib)', re.IGNORECASE)
    dlls_mkl = [f for f in os.listdir(lib_dir) if re_mkllib.match(f)]
    if dlls_mkl:
        logger = logging.getLogger(__name__)
        logger.info("MKL libraries found when importing numpy. Adding MKL to binaries")
        binaries += [(os.path.join(lib_dir, f), '.') for f in dlls_mkl]
