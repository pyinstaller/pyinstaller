#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Replace the code of real 'site' module by fake code doing nothing.

The real 'site' does some magic to find paths to other possible
Python modules. We do not want this behaviour for frozen applications.

Fake 'site' makes PyInstaller to work with distutils and to work inside
virtualenv environment.
"""

import os

from PyInstaller.utils.hooks import logger
from PyInstaller import PACKAGEPATH

def pre_find_module_path(api):
    #FIXME: For reusability, move this into a new
    #PyInstaller.configure.get_fake_modules_dir() utility function.
    # Absolute path of the faked sub-package.
    fake_dir = os.path.join(PACKAGEPATH, 'fake-modules')

    api.search_dirs = [fake_dir]
    logger.info('site: retargeting to fake-dir %r', fake_dir)
