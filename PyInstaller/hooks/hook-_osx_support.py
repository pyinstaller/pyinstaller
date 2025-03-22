#-----------------------------------------------------------------------------
# Copyright (c) 2025, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Prevent conditional import of `distutils` in `_osx_support.compiler_fixup()` in python < 3.10 from pulling in
# `distutils`; this function is called only from `distutils` itself, which ensures that the module is available as
# needed. Blocking this import prevents `distutils` (and nowadays `setuptools`) from being pulled into even very
# basic applications when built with python < 3.10.
#
# See: https://github.com/python/cpython/blob/f3994ade31a563d49806cf6a681d1b1115fccaa3/Lib/_osx_support.py#L430-L434

excludedimports = ['distutils']
