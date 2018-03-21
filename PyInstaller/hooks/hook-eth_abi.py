#-----------------------------------------------------------------------------
# Copyright (c) 2018-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for the eth-abi package: https://pypi.python.org/pypi/eth-abi
# Tested with eth-utils 0.5.0 and Python 3.5.2, on Ubuntu Linux x64

from PyInstaller.utils.hooks import copy_metadata

datas = copy_metadata("eth_abi")
