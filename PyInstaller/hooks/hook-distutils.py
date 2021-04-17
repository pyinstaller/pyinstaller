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

"""
`distutils`-specific post-import hook.

This hook freezes the external `Makefile` and `pyconfig.h` files bundled with
the active Python interpreter, which the `distutils.sysconfig` module parses at
runtime for platform-specific metadata.
"""

from PyInstaller import compat

# From Python 3.6 and later ``distutils.sysconfig`` takes on the same
# behaviour as regular ``sysconfig`` of moving the config vars to a
# module (see hook-sysconfig.py). It doesn't use a nice
# `get module name` function like ``sysconfig`` does to help us
# locate it but the module is the same file that ``sysconfig`` uses so
# we can use the ``_get_sysconfigdata_name()`` from regular ``sysconfig``.
import sysconfig
if not compat.is_win and hasattr(sysconfig, '_get_sysconfigdata_name'):
    hiddenimports = [sysconfig._get_sysconfigdata_name()]
