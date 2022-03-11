#-----------------------------------------------------------------------------
# Copyright (c) 2005-2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Replace the code of real 'site' module by fake code doing nothing.

The real 'site' does some magic to find paths to other possible Python modules.
We do not want this behaviour for frozen applications.

Fake 'site' makes PyInstaller to work with distutils and to work inside virtualenv environment.
"""

import os

from PyInstaller import PACKAGEPATH
from PyInstaller.utils.hooks import logger


def pre_find_module_path(api):
    # FIXME: for reusability, move this into a new PyInstaller.configure.get_fake_modules_dir() utility function.
    # Absolute path of the faked sub-package.
    fake_dir = os.path.join(PACKAGEPATH, 'fake-modules')

    api.search_dirs = [fake_dir]
    logger.info('site: retargeting to fake-dir %r', fake_dir)
