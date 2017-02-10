#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Problem appears to be that pyinstaller cannot have two modules of the same
name that differ only by lower/upper case.  The from the future 'queue' simply
imports all of the 'Queue' module.  So, here we force the 'Queue' module to be
imported.
"""

from PyInstaller.compat import is_py2

if is_py2:
    # force import of Python 2.7 Queue module
    hiddenimports = ['Queue']

