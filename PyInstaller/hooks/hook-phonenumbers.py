#-----------------------------------------------------------------------------
# Copyright (c) 2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# Hook for the phonenumbers package: https://pypi.org/project/phonenumbers/
#
# Tested with phonenumbers 8.9.7 and Python 3.6.1, on Ubuntu 16.04 64bit.

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('phonenumbers')
