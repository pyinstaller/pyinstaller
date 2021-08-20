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

This hook freezes the external `Makefile` and `pyconfig.h` files bundled with the active Python interpreter, which the
`distutils.sysconfig` module parses at runtime for platform-specific metadata.
"""

# From Python 3.6 and later ``distutils.sysconfig`` takes on the same behaviour as regular ``sysconfig`` of moving the
# config vars to a module (see hook-sysconfig.py). It doesn't use a nice `get module name` function like ``sysconfig``
# does to help us locate it but the module is the same file that ``sysconfig`` uses so we can use the
# ``_get_sysconfigdata_name()`` from regular ``sysconfig``.
try:
    import sysconfig
    hiddenimports = [sysconfig._get_sysconfigdata_name()]
except AttributeError:
    # Either sysconfig has no attribute _get_sysconfigdata_name (i.e., the function does not exist), or this is Windows
    # and the _get_sysconfigdata_name() call failed due to missing sys.abiflags attribute.
    pass
