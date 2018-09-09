#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for the zeep module: https://pypi.python.org/pypi/zeep
# Tested with zeep 0.13.0, Python 2.7, Windows

from PyInstaller.utils.hooks import copy_metadata
datas = copy_metadata('zeep')
