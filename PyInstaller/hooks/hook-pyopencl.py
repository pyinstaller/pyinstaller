#-----------------------------------------------------------------------------
# Copyright (c) 2015-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Hook for the pyopencl module: https://github.com/pyopencl/pyopencl

from PyInstaller.utils.hooks import copy_metadata, collect_data_files
datas = copy_metadata('pyopencl')
datas += collect_data_files('pyopencl')
