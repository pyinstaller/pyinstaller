#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from __future__ import print_function

# sys.path  should contain absolute paths.
# With relative paths frozen application will
# fail to import modules when currect working
# directory is changed.


import os

import sys
import tempfile


# Python 3 does not have function os.getcwdu() since all strings are unicode.
getcwd = os.getcwdu if sys.version_info[0] < 3 else os.getcwd


print('sys.stderr.encoding:', sys.stderr.encoding)
print('sys.path', sys.path)
print('CWD:', repr(getcwd()))

# Change working directory.
os.chdir(tempfile.gettempdir())
print('Changing working directory...')
print('CWD:', repr(getcwd()))

# Try import a module. It should fail
try:
    for pth in sys.path:
        if not os.path.isabs(pth):
            raise SystemExit('ERROR: sys.path not absolute')
    import datetime
except:
    raise SystemExit('ERROR: sys.path not absolute')
