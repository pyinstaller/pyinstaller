#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# pyodbc is a binary Python module. On Windows when installed with easy_install
# it is installed as zipped Python egg. This binary module is extracted
# to PYTHON_EGG_CACHE directory. PyInstaller should find the binary there and
# include it with frozen executable.


import pyodbc
