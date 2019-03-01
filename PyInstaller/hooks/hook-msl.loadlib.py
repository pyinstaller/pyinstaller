#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# msl-loadlib requires some binaries to work properly. Basically, it allows cross
# loading DLLs by spawning a 32/64 bit python, and loading the dll there. This
# means you can load a 32bit dll from 64bit python, and vice versa.
# Calls to the DLL can then be proxied through the other python instance.

from PyInstaller.utils.hooks import collect_data_files
datas = collect_data_files('msl.loadlib')
