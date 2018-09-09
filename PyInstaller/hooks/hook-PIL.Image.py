#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# This hook was tested with Pillow 2.9.0 (Maintained fork of PIL):
# https://pypi.python.org/pypi/Pillow

from PyInstaller.utils.hooks import collect_submodules

# Include all PIL image plugins - module names containing 'ImagePlugin'.
# e.g.  PIL.JpegImagePlugin
hiddenimports = collect_submodules('PIL', lambda name: 'ImagePlugin' in name)
