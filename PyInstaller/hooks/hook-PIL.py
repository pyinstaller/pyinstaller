#-----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# This hook was tested with Pillow 2.9.0 (Maintained fork of PIL):
# https://pypi.python.org/pypi/Pillow

from PyInstaller.compat import modname_tkinter

# Ignore 'FixTk' (Python 2) or tkinter to prevent inclusion of Tcl/Tk library
# and other GUI libraries.
# Assume that if people are really using tkinter in their application, they
# will also import it directly and thus PyInstaller bundles the right GUI
# library.
excludedimports = [modname_tkinter, 'FixTk', 'PySide', 'PyQt4', 'PyQt5']
