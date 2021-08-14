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

import win32api


def check_shortpathname(fn):
    lfn = win32api.GetLongPathNameW(fn)
    fn = os.path.normcase(fn)
    lfn = os.path.normcase(lfn)
    if lfn != fn:
        print("ShortPathName: Expected %s, got %s" % (fn, lfn))
        raise SystemExit(-1)


print("sys.executable:", ascii(sys.executable))

if not os.path.exists(sys.executable):
    raise SystemExit("sys.executable does not exist.")
check_shortpathname(sys.executable)

print("sys.argv[0]:", ascii(sys.argv[0]))

if not os.path.exists(sys.argv[0]):
    raise SystemExit("sys.argv[0] does not exist.")
check_shortpathname(sys.argv[0])

print("sys._MEIPASS:", ascii(sys._MEIPASS))

if not os.path.exists(sys._MEIPASS):
    raise SystemExit("sys._MEIPASS does not exist.")
tmp = os.path.normcase(win32api.GetTempPath())
if os.path.normcase(win32api.GetLongPathNameW(tmp)) == tmp:
    # Test only if TempPath is not a short path. This might for example happen if
    # TMP=c:\users\runner~1\appdata\local\temp, due to  username being too long.
    check_shortpathname(sys._MEIPASS)
