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

def is_shortpathname(fn):
    return fn == win32api.GetLongPathNameW(fn)

print("sys.executable: %s" % safe_repr(sys.executable))

if not os.path.exists(sys.executable):
    raise SystemExit("sys.executable does not exist.")
if not is_shortpathname(sys.executable):
    raise SystemExit("sys.executable is a ShortPathName.")

print("sys.argv[0]: %s" % safe_repr(sys.argv[0]))

if not os.path.exists(sys.argv[0]):
    raise SystemExit("sys.argv[0] does not exist.")
if not is_shortpathname(sys.argv[0]):
    raise SystemExit("sys.argv[0] is a ShortPathName.")

print("sys._MEIPASS: %s" % safe_repr(sys._MEIPASS))

if not os.path.exists(sys._MEIPASS):
    raise SystemExit("sys._MEIPASS does not exist.")
if not is_shortpathname(sys._MEIPASS):
    raise SystemExit("sys._MEIPASS is a ShortPathName.")

