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

# This script is used by multiple tests.
# It checks that various paths set by the bootloader are usable filenames.

import sys
import os

print("sys.executable:", ascii(sys.executable))

if not os.path.exists(sys.executable):
    raise SystemExit("sys.executable does not exist.")

print("sys.argv[0]:", ascii(sys.argv[0]))

if not os.path.exists(sys.argv[0]):
    raise SystemExit("sys.argv[0] does not exist.")

print("sys._MEIPASS:", ascii(sys._MEIPASS))

if not os.path.exists(sys._MEIPASS):
    raise SystemExit("sys._MEIPASS does not exist.")
