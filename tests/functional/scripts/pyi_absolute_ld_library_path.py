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

import os
import sys

# Bootloader should override/set LD_LIBRARY_PATH (Linux, Solaris, AIX, and other Unixes only).
libpath = sys._MEIPASS

# The name of the environment variable used to define the path where the OS should search for dynamic libraries.
if sys.platform.startswith('aix'):
    libpath_var_name = 'LIBPATH'
else:
    libpath_var_name = 'LD_LIBRARY_PATH'

orig_libpath = os.environ.get(libpath_var_name + "_ORIG")
if orig_libpath:
    libpath += ':' + orig_libpath
print(('LD_LIBRARY_PATH expected: ' + libpath))

libpath_from_env = os.environ.get(libpath_var_name)
print(('LD_LIBRARY_PATH  current: ' + libpath_from_env))

if not libpath == libpath_from_env:
    raise SystemExit("Expected LD_LIBRARY_PATH doesn't match.")

# LD_LIBRARY_PATH set by bootloader should be an absolute path.
part1 = libpath_from_env.split(os.pathsep, 1)[0]
print('First path element:', part1)
if not os.path.isabs(part1):
    raise SystemExit("LD_LIBRARY_PATH is not an absolute path.")
