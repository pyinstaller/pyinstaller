#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Test the value of the __file__ attribute; for a frozen package, it should be:
#   sys.prefix/package/__init__.py
# and for a frozen module, it should be:
#   sys.prefix/module.py

import os
import sys

import shutil as module
import xml.sax as package

expected_mod = os.path.join(sys.prefix, 'shutil.py')
expected_pkg = os.path.join(sys.prefix, 'xml', 'sax', '__init__.py')

# Print.
print(f'Actual   mod.__file__: {module.__file__}', file=sys.stderr)
print(f'Expected mod.__file__: {expected_mod}', file=sys.stderr)
print(f'Actual   pkg.__file__: {package.__file__}', file=sys.stderr)
print(f'Expected pkg.__file__: {expected_pkg}', file=sys.stderr)

# Compare.
# NOTE: use os.path.normpath() to ensure invariance w.r.t. separator, which may differ between what is used by
# bootloader and python itself - for example, under msys2/mingw python on Windows.
if os.path.normpath(module.__file__) != os.path.normpath(expected_mod):
    raise SystemExit('MODULE.__file__ attribute is wrong.')
if os.path.normpath(package.__file__) != os.path.normpath(expected_pkg):
    raise SystemExit('PACKAGE.__file__ attribute is wrong.')
