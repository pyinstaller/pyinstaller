# -----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------

"""
`distutils`-specific pre-find module path hook.

When run from within a venv (virtual environment), this hook changes the
`__path__` of the `distutils` package to that of the system-wide rather than
venv-specific `distutils` package. While the former is suitable for freezing,
the latter is intended for use _only_ from within venvs.
"""


import distutils
import os
import sys

from PyInstaller.utils.hooks import logger
from PyInstaller import compat


def pre_find_module_path(api):
    # Absolute path of the system-wide "distutils" package when run from within
    # a venv or None otherwise.

    if not compat.is_venv:
        return

    # According to python docs, the system libraries should be in
    # <sys.prefix>/lib/pythonX.Y, but this doesn't seem to be the
    # case in windows...
    if compat.is_win:
        system_module_path = os.path.join(compat.base_prefix, 'Lib')
    else:
        system_module_path = os.path.join(compat.base_prefix, 'lib',
                                          'python' + sys.version[:3])

    api.search_dirs = [system_module_path]
    logger.info('distutils: retargeting to non-venv dir %r',
                system_module_path)
