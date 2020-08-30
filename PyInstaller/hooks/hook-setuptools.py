#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


from PyInstaller.compat import is_unix, is_darwin
from PyInstaller.utils.hooks import collect_submodules

excludedimports = ["setuptools.py27compat", "setuptools.py33compat"]

hiddenimports = [
    # Test case import/test_zipimport2 fails during importing
    # pkg_resources or setuptools when module not present.
    'distutils.command.build_ext',
    'setuptools.msvc',
]

# Necessary for setuptools on Mac/Unix
if is_unix or is_darwin:
    hiddenimports.append('syslog')

# setuptools >= 39.0.0 is "vendoring" its own direct dependencies from
# "_vendor" to "extern". This also requires
# 'pre_safe_import_module/hook-setuptools.extern.six.moves.py' to make the
# moves defined in 'setuptools._vendor.six' importable under
# 'setuptools.extern.six'.
hiddenimports.extend(collect_submodules('setuptools._vendor'))
