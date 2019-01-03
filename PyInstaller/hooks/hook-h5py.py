#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Hook for http://pypi.python.org/pypi/h5py/
"""


hiddenimports = ['h5py._proxy', 'h5py.utils', 'h5py.defs', 'h5py.h5ac']
