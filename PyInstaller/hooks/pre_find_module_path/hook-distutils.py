# -----------------------------------------------------------------------------
# Copyright (c) 2005-2022, PyInstaller Development Team.
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

When run from within a venv (virtual environment), this hook changes the `__path__` of the `distutils` package to
that of the system-wide rather than venv-specific `distutils` package. While the former is suitable for freezing,
the latter is intended for use _only_ from within venvs. This applies only to venvs created by (earlier versions
of?) virtualenv.
"""

import os

from PyInstaller.utils.hooks import logger
from PyInstaller.utils.hooks import get_module_file_attribute


def pre_find_module_path(api):
    # Absolute path of the system-wide "distutils" package when run from within a venv or None otherwise.

    # opcode is not a virtualenv module, so we can use it to find the stdlib. Technique taken from virtualenv's
    # "distutils" package detection at
    # https://github.com/pypa/virtualenv/blob/16.3.0/virtualenv_embedded/distutils-init.py#L5
    stdlib_path = os.path.normpath(os.path.dirname(get_module_file_attribute("opcode")))

    # Resolve path to the distutils package (the parent of distutils' __init__.py). There are three known possibilites:
    #  1. when using distutils from python's stdlib, this points to the <path/to/stdlib>/distutils
    #  2. under virtual environments created by (older versions of?) `virtualenv`, this may point to the virtualenv's
    #     distutils wrapper, located in <path/to/venv>/lib/python3.x/distutils
    #  3. recent versions of setuptools override stdlib's distutils with their own vendored copy (unless the
    #     SETUPTOOLS_USE_DISTUTILS environment variable is set to something else than "local"). In this case, the
    #     obtained path points to <path/to/site-packages>/setuptools/_distutils
    #
    # In practice, we care only about cases 1 and 2 here, because if using setuptools-provided distutils, our distutils
    # pre-safe-import-module hook marks the distutils as runtime module, and inhibits its further analysis (so this
    # hook is never reached).
    distutils_path = os.path.normpath(os.path.dirname(get_module_file_attribute("distutils")))

    # The parent path of distutils package. Used in comparison against stdlib_path to determine if we are dealing with
    # case no. 2.
    distutils_parent_path = os.path.dirname(distutils_path)

    if distutils_parent_path != stdlib_path:
        # Case no. 2; retarget to stdlib version. If there was a setuptools-provided version available, this would be
        # reflected in distutils_path and we would not hit this branch.
        api.search_dirs = [stdlib_path]
        logger.info('distutils: retargeting to non-virtualenv copy (%r)', os.path.join(stdlib_path, 'distutils'))
    else:
        # Case no. 1
        logger.info('distutils: using stdlib copy (%r)', distutils_path)
