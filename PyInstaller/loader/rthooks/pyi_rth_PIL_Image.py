#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys
import pyi_importers


# Find FrozenImporter object from sys.meta_path.
importer = None
for obj in sys.meta_path:
    if isinstance(obj, pyi_importers.FrozenImporter):
        importer = obj
        break


# Explicitly import all PIL `PIL.*ImagePlugin` modules.
for name in importer.toc:
    if name.startswith('PIL.') and name.endswith('ImagePlugin'):
        __import__(name)
