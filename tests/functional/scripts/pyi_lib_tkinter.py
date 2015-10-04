#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Ensure environment variables TCL_LIBRARY and TK_LIBRARY are set properly.
# and data files are bundled.


import glob
import os


# In Python 3 module name is 'tkinter'
try:
    from tkinter import *
except ImportError:
    from Tkinter import *


def compare(test_name, expect, frozen):
    expect = os.path.normpath(expect)
    print(test_name)
    print(('  Expected: ' + expect))
    print(('  Current:  ' + frozen))
    print('')
    # Path must match.
    if not frozen == expect:
        raise SystemExit('Data directory is not set properly.')
    # Directory must exist.
    if not os.path.exists(frozen):
        raise SystemExit('Data directory does not exist.')
    # Directory must contain some .tcl files and not to be empty.
    if not len(glob.glob(frozen + '/*.tcl')) > 0:
        raise SystemExit('Data directory does not contain .tcl files.')


tcl_dir = os.environ['TCL_LIBRARY']
tk_dir = os.environ['TK_LIBRARY']


compare('Tcl', os.path.join(sys.prefix, 'tcl'), tcl_dir)
compare('Tk', os.path.join(sys.prefix, 'tk'), tk_dir)
