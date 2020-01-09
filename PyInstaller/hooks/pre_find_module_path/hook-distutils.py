# -----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
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

from PyInstaller.utils.hooks import logger


def pre_find_module_path(api):
    # Absolute path of the system-wide "distutils" package when run from within
    # a venv or None otherwise.

    # opcode is not a virtualenv module, so we can use it to find the stdlib.
    # Technique taken from virtualenv's "distutils" package detection at
    # https://github.com/pypa/virtualenv/blob/16.3.0/virtualenv_embedded/distutils-init.py#L5
    import opcode

    system_module_path = os.path.normpath(os.path.dirname(opcode.__file__))
    loaded_module_path = os.path.normpath(os.path.dirname(distutils.__file__))
    if system_module_path != loaded_module_path:
        # Find this package in its parent directory.
        api.search_dirs = [system_module_path]
        logger.info('distutils: retargeting to non-venv dir %r',
                    system_module_path)
