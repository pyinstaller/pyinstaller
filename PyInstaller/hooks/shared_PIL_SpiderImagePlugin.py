#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
PIL's SpiderImagePlugin features a tkPhotoImage() method which imports
ImageTk (and thus brings the whole Tcl/Tk library in).
We cheat a little and remove the ImageTk import: I assume that if people
are really using ImageTk in their application, they will also import it
directly.
"""


def hook(mod):
    for i, m in enumerate(mod.pyinstaller_imports):
        # Ignore these two modules to not include whole Tk or Qt stack.
        # If these modules should be included then they will definitely
        # be dependency as any other module.
        if m[0] ==  'ImageTk':
            del mod.pyinstaller_imports[i]
            break
    return mod
