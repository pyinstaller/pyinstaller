#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# This hook was tested with Pillow 2.9.0 (Maintained fork of PIL):
# https://pypi.python.org/pypi/Pillow

from PyInstaller.compat import modname_tkinter
from PyInstaller.utils.hooks import collect_submodules


# Ignore 'FixTk' (Python 2) or tkinter to prevent inclusion of Tcl/Tk library.
# Assume that if people are really using tkinter in their application, they
# will also import it directly.
excludedimports = [modname_tkinter, 'FixTk']
# Include all PIL image plugins - module names containing 'ImagePlugin'.
# e.g.  PIL.JpegImagePlugin
hiddenimports = collect_submodules('PIL', pattern='ImagePlugin')
