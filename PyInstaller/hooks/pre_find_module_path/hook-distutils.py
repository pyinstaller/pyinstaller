#-----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
`distutils`-specific pre-find module path hook.

When run from within a venv (virtual environment), this hook changes the
`__path__` of the `distutils` package to that of the system-wide rather than
venv-specific `distutils` package. While the former is suitable for freezing,
the latter is intended for use _only_ from within venvs.
"""


import distutils
import os

from PyInstaller.utils.hooks import logger


def pre_find_module_path(api):
    # Absolute path of the system-wide "distutils" package when run from within
    # a venv or None otherwise.
    distutils_dir = getattr(distutils, 'distutils_path', None)
    if distutils_dir is not None:
        # Find this package in its parent directory.
        api.search_dirs = [os.path.dirname(distutils_dir)]
        logger.info('distutils: retargeting to non-venv dir %r' % distutils_dir)
