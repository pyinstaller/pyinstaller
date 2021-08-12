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

# PyInstaller always loads modules from the embedded archive before looking at sys.path.
#
# This tests creates a module with the same name as the one in the embbedded archive. The frozen application
# should always load the module from the embedded archive.

import os
import sys
import importlib

# Create module.
txt = """
x = %d
"""
mod_filename = os.path.join(sys._MEIPASS, 'data_reload.py')
with open(mod_filename, 'w') as f:
    f.write(txt % 2)

# Import created module.
import data_reload  # noqa: E402

orig_x = data_reload.x
print(('data_reload.x is %s' % data_reload.x))

# Modify code of module - increment x.
with open(mod_filename, 'w') as f:
    f.write(txt % (data_reload.x + 1))

# Reload module.
importlib.reload(data_reload)
print(('data_reload.x is now %s' % data_reload.x))
# The value of 'x' should be the orig_x + 1.
assert data_reload.x == orig_x + 1
