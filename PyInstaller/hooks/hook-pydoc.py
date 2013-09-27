#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Python module 'pydoc' causes the inclusion of Tcl/Tk library even in case
of simple hello_world script. Most of the we do not want this behavior.

This hook just removes this implicit dependency on Tcl/Tk.
"""


def hook(mod):
    # Ignore 'Tkinter' to prevent inclusion of Tcl/Tk library.
    for i, m in enumerate(mod.imports):
        if m[0] == 'Tkinter':
            del mod.imports[i]
            break
    return mod
