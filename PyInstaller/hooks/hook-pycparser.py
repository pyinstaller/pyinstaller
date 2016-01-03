#-----------------------------------------------------------------------------
# Copyright (c) 2014-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# pycparser needs two modules -- lextab.py and yacctab.py -- which it
# generates at runtime if they cannot be imported.
#
# Those modules are written to the current working directory for which
# the running process may not have write permissions, leading to a runtime
# exception.
#
# This hook tells pyinstaller about those hidden imports, avoiding the
# possibility of such runtime failures.

hiddenimports = ['pycparser.lextab', 'pycparser.yacctab']
