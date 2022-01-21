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

# Ensure that environment variables TCL_LIBRARY and TK_LIBRARY are set properly, and that data files are collected.
# NOTE: "library" here refers to the scripts directory as in "collection", not as a dynamic/shared library.

# NOTE: on macOS, we do collect Tcl/Tk files when the _tkinter module is linked against system copy of Tcl/Tk framework.
# In that case, TCL_LIBRARY and TK_LIBRARY environment variables are not set by the runtime hook, and this test is
# reduced to a basic "import tkinter" test.

import glob
import os
import sys

import tkinter  # noqa: F401


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


# Tcl scripts directory
tcl_dir = os.environ.get('TCL_LIBRARY')
if tcl_dir:
    compare('Tcl', os.path.join(sys.prefix, 'tcl'), tcl_dir)
elif sys.platform != 'darwin':
    raise SystemExit("TCL_LIBRARY environment variable is not set!")

# Tk scripts directory
tk_dir = os.environ.get('TK_LIBRARY')
if tk_dir:
    compare('Tk', os.path.join(sys.prefix, 'tk'), tk_dir)
elif sys.platform != 'darwin':
    raise SystemExit("TK_LIBRARY environment variable is not set!")
