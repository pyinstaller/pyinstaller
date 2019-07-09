#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import sys


try:
    FileNotFoundError
except NameError:
    # FileNotFoundError is new in Python 3.0
    # NB: Aliasing IOError is not a full emulation of FileNotFoundError,
    # but far enough for this usecase, where the whole frozen program
    # terminates when this exception occurs.
    FileNotFoundError = IOError

tcldir = os.path.join(sys._MEIPASS, 'tcl')
tkdir = os.path.join(sys._MEIPASS, 'tk')

if not os.path.isdir(tcldir):
    raise FileNotFoundError('Tcl data directory "%s" not found.' % (tcldir))
if not os.path.isdir(tkdir):
    raise FileNotFoundError('Tk data directory "%s" not found.' % (tkdir))

# Notify "tkinter" of such directories.
os.environ["TCL_LIBRARY"] = tcldir
os.environ["TK_LIBRARY"] = tkdir
