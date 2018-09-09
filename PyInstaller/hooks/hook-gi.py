#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
"""
Import hook for PyGObject https://wiki.gnome.org/PyGObject

Tested with PyGObject 3.16.2 from MacPorts on Mac OS X 10.10 and
PyGobject 3.14.0 on Windows 7
"""

hiddenimports = ['gi._error', 'gi._option']
