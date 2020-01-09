#-----------------------------------------------------------------------------
# Copyright (c) 2019-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
`importlib_resources` is a backport of the 3.7+ module `importlib.resources`
"""

import os
from PyInstaller.compat import is_py2, is_py3, is_py37
from PyInstaller.utils.hooks import get_module_file_attribute

# Include the version.txt file, used to set __version__
res_loc = os.path.dirname(get_module_file_attribute('importlib_resources'))
datas = [
    (os.path.join(res_loc, 'version.txt'), 'importlib_resources'),
]

# Replicate the module's version checks to exclude unused modules.
if is_py37:
    # Stdlib now has the implmentation of this, so the backports
    # aren't used at all
    excludedmodules = [
        'importlib_resources._py2',
        'importlib_resources._py3',
    ]
elif is_py3:
    excludedmodules = ['importlib_resources._py2']
elif is_py2:
    excludedmodules = ['importlib_resources._py3']
