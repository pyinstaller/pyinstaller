#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Hook for the diStorm3 module: https://pypi.python.org/pypi/distorm3
# Tested with distorm3 3.3.0, Python 2.7, Windows

from PyInstaller.utils.hooks import collect_dynamic_libs

# distorm3 dynamic library should be in the path with other dynamic libraries.
binaries = collect_dynamic_libs('distorm3', destdir='.')
