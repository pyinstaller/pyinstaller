#-----------------------------------------------------------------------------
# Copyright (c) 2019-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
`importlib_resources` is a backport of the 3.9+ module `importlib.resources`
"""

import os
from PyInstaller.utils.hooks import get_module_file_attribute, \
    is_module_satisfies

if is_module_satisfies("importlib_resources >= 1.2.0"):
    # since 1.2.0 importlib.metadata is used which PyInstaller knows how to
    # handle.
    pass
else:
    # include the version.txt file, used to set __version__
    res_loc = os.path.dirname(get_module_file_attribute('importlib_resources'))
    datas = [
        (os.path.join(res_loc, 'version.txt'), 'importlib_resources'),
    ]

if is_module_satisfies("importlib_resources >= 1.3.1"):
    hiddenimports = ['importlib_resources.trees']

# this is only required for python2 support
excludedimports = ['importlib_resources._py2']
