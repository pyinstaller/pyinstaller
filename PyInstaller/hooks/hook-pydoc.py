#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Python 2 module 'pydoc' causes the inclusion of Tcl/Tk library even in case
of simple hello_world script. Most of the we do not want this behavior.
'pydoc' from Python 3 does not have this dependency.

This hook just removes this implicit dependency on Tcl/Tk.
"""

from PyInstaller.compat import is_py2, modname_tkinter


# Ignore 'Tkinter' to prevent inclusion of Tcl/Tk library.
if is_py2:
    excludedimports = [modname_tkinter]
