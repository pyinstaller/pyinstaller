#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------


import os
import sys

tcldir = os.path.join(sys._MEIPASS, 'tcl')
tkdir = os.path.join(sys._MEIPASS, 'tk')

if not os.path.isdir(tcldir):
    raise FileNotFoundError('Tcl data directory "%s" not found.' % (tcldir))
if not os.path.isdir(tkdir):
    raise FileNotFoundError('Tk data directory "%s" not found.' % (tkdir))

# Notify "tkinter" of such directories.
os.environ["TCL_LIBRARY"] = tcldir
os.environ["TK_LIBRARY"] = tkdir
