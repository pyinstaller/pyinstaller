#-----------------------------------------------------------------------------
# Copyright (c) 2015-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Hook for the pyopencl module: https://github.com/pyopencl/pyopencl

from PyInstaller.utils.hooks import copy_metadata, collect_data_files
datas = copy_metadata('pyopencl')
datas += collect_data_files('pyopencl')
