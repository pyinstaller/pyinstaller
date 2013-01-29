#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import sys


basedir = sys._MEIPASS


tcldir = os.path.join(basedir, '_MEI', 'tcl')
tkdir = os.path.join(basedir, '_MEI', 'tk')


# Directories with .tcl files.
os.environ["TCL_LIBRARY"] = tcldir
os.environ["TK_LIBRARY"] = tkdir
