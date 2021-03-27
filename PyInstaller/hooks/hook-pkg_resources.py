#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
from PyInstaller.utils.hooks import collect_submodules

# pkg_resources keeps vendored modules in its _vendor subpackage, and does
# sys.meta_path based import magic to expose them as pkg_resources.extern.*
hiddenimports = collect_submodules('pkg_resources._vendor')

# pkg_resources v45.0 dropped support for Python 2 and added this
# module printing a warning. We could save some bytes if we would
# replace this by a fake module.
hiddenimports.append('pkg_resources.py2_warn')

excludedimports = ['__main__']

# Some more hidden imports. See:
# https://github.com/pyinstaller/pyinstaller-hooks-contrib/issues/15#issuecomment-663699288
# `packaging` can either be its own package, or embeded in
# `pkg_resources._vendor.packaging`, or both.
# Assume the worst and include both if present.
hiddenimports += collect_submodules('packaging')

hiddenimports += ['pkg_resources.markers']
