#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# PyInstaller always loads modules from the embedded archive before
# looking at sys.path.
#
# This tests creates module with the same name as the one in the
# embbedded archive. Python should always load module from the
# embedded archive.


# imp module is deprecated since Python 3.4.
try:
    import importlib as imp
    # Python 3.3 does not have function importlib.reload().
    if not hasattr(imp, 'reload'):
        raise ImportError
except ImportError:
    import imp
import os
import sys


# Create module.
txt = """
x = %d
"""
mod_filename = os.path.join(sys._MEIPASS, 'data_reload.py')
with open(mod_filename, 'w') as f:
    f.write(txt % 2)


# Import created module.
import data_reload
orig_x = data_reload.x
print(('data_reload.x is %s' % data_reload.x))


# Modify code of module - increment x.
with open(mod_filename, 'w') as f:
    f.write(txt % (data_reload.x + 1))

# Reload module.
imp.reload(data_reload)
print(('data_reload.x is now %s' % data_reload.x))
# The value of 'x' should be the orig_x + 1.
assert data_reload.x == orig_x + 1
