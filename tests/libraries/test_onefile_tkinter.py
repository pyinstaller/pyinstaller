#
# Copyright (C) 2012, Martin Zibricky
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


# Ensure environment variables TCL_LIBRARY and TK_LIBRARY are set properly.
# and data files are bundled.


import glob
import os
import sys

from Tkinter import *


def compare(test_name, expect, frozen):
    expect = os.path.normpath(expect)
    print(test_name)
    print('  Expected: ' + expect)
    print('  Current:  ' + frozen)
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


compare('Tcl', os.path.join(sys.prefix, '_MEI', 'tcl'), tcl_dir)
compare('Tk', os.path.join(sys.prefix, '_MEI', 'tk'), tk_dir)
