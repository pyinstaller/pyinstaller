#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# LD_LIBRARY_PATH set by bootloader should not contain ./
#
# This test assumes the LD_LIBRARY_PATH is not set before running the test.
# If you experience that this test fails, try to unset the variable and
# rerun the test.
#
# This is how it is done in bash:
#
#  $ cd buildtests
#  $ unset LD_LIBRARY_PATH
#  $ ./runtests.py basic/test_absolute_ld_library_path.py


import os
import sys


# Bootloader should override set LD_LIBRARY_PATH.

# For Linux, Solaris, AIX and other Unixes only
libpath = sys._MEIPASS

# The name of the environment variable used to define the path where the
# OS should search for dynamic libraries.
if sys.platform.startswith('aix'):
    libpath_var_name = 'LIBPATH'
else:
    libpath_var_name = 'LD_LIBRARY_PATH'

print(('LD_LIBRARY_PATH expected: ' + libpath))

libpath_from_env = os.environ.get(libpath_var_name)
print(('LD_LIBRARY_PATH  current: ' + libpath_from_env))

if not libpath == libpath_from_env:
    raise SystemExit("Expected LD_LIBRARY_PATH doesn't match.")
