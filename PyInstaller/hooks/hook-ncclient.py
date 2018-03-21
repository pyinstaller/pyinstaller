#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Hook for ncclient. ncclient is a Python library that facilitates client-side
scripting and application development around the NETCONF protocol.
https://pypi.python.org/pypi/ncclient

This hook was tested with ncclient 0.4.3.
"""
from PyInstaller.utils.hooks import collect_submodules

# Modules 'ncclient.devices.*' are dynamically loaded and PyInstaller
# is not able to find them.
hiddenimports = collect_submodules('ncclient.devices')


