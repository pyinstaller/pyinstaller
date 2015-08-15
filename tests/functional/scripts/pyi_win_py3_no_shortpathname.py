#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# This script is used by multiple tests. It checks that various paths set by the
# bootloader are usable filenames.

import sys, os, win32api

if sys.version_info[0] == 2:
    safe_repr = repr
else:
    safe_repr = ascii

def check_shortpathname(fn):
    lfn = win32api.GetLongPathNameW(fn)
    fn = os.path.normcase(fn)
    lfn = os.path.normcase(lfn)
    if lfn != fn:
        print("ShortPathName: Expected %s, got %s" % (fn, lfn))
        raise SystemExit(-1)

print("sys.executable: %s" % safe_repr(sys.executable))

if not os.path.exists(sys.executable):
    raise SystemExit("sys.executable does not exist.")
check_shortpathname(sys.executable)

print("sys.argv[0]: %s" % safe_repr(sys.argv[0]))

if not os.path.exists(sys.argv[0]):
    raise SystemExit("sys.argv[0] does not exist.")
check_shortpathname(sys.argv[0])

print("sys._MEIPASS: %s" % safe_repr(sys._MEIPASS))

if not os.path.exists(sys._MEIPASS):
    raise SystemExit("sys._MEIPASS does not exist.")
check_shortpathname(sys._MEIPASS)

