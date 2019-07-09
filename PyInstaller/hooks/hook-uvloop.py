#-----------------------------------------------------------------------------
# Copyright (c) 2017-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# Hook for the uvloop package: https://pypi.python.org/pypi/uvloop
#
# Tested with uvloop 0.8.1 and Python 3.6.2, on Ubuntu 16.04.1 64bit.

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('uvloop')
