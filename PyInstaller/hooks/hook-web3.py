#-----------------------------------------------------------------------------
# Copyright (c) 2018-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for the web3 package: https://pypi.python.org/pypi/web3
# Tested with web3 3.16.5 and Python 3.5.2, on Ubuntu Linux x64

from PyInstaller.utils.hooks import copy_metadata

datas = copy_metadata("web3")
