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

# sys.path should contain absolute paths. With relative paths, the frozen application will fail to import modules when
# current working directory is changed.

import os
import sys
import tempfile

print('sys.stderr.encoding:', sys.stderr.encoding)
print('sys.path', sys.path)
print('CWD:', repr(os.getcwd()))

# Change working directory.
os.chdir(tempfile.gettempdir())
print('Changing working directory...')
print('CWD:', repr(os.getcwd()))

# Try import a module. It should fail
try:
    for pth in sys.path:
        if not os.path.isabs(pth):
            raise SystemExit('ERROR: sys.path not absolute')
    import datetime  # noqa: F401
except Exception:
    raise SystemExit('ERROR: sys.path not absolute')
