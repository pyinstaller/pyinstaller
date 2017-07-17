#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
"""
Hook for http://pypi.python.org/pypi/h5py/
"""

hiddenimports = [
    '_proxy',
    'utils',
    'defs',
    'h5ac',
    'h5py.defs',
    'h5py.h5',
    'h5py.h5a',
    'h5py.h5ac',
    'h5py.h5d',
    'h5py.h5ds',
    'h5py.h5f',
    'h5py.h5fd',
    'h5py.h5g',
    'h5py.h5i',
    'h5py.h5l',
    'h5py.h5o',
    'h5py.h5p',
    'h5py.h5r',
    'h5py.h5s',
    'h5py.h5t',
    'h5py.h5z',
    'h5py.utils',
    'h5py._conv',
    'h5py._errors',
    'h5py._objects',
    'h5py._proxy',
]
# hdf5.dll
# hdf5_hl.dll