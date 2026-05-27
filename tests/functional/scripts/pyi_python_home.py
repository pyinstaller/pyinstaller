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

# PYTHONHOME (sys.prefix) has to be same as sys._MEIPASS.

import os
import sys

PATHS_TO_TEST = ['prefix', 'exec_prefix', 'base_prefix', 'base_exec_prefix']

# Display all paths before doing actual comparison
print(f"sys._MEIPASS: {sys._MEIPASS!r}", file=sys.stderr)
for name in PATHS_TO_TEST:
    print(f"sys.{name}: {getattr(sys, name)!r}", file=sys.stderr)

# NOTE: use os.path.normpath() to ensure invariance w.r.t. separator, which may differ between what is used by
# bootloader and python itself - for example, under msys2/mingw python on Windows.
for name in PATHS_TO_TEST:
    path = os.path.normpath(getattr(sys, name))
    if path != os.path.normpath(sys._MEIPASS):
        raise SystemExit(f"sys.{name} ({path!r}) != sys._MEIPASS ({sys._MEIPASS!r})")
