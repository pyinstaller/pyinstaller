#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# When PyQt5.Qt is imported it implies the import of all PyQt5 modules. See
# http://pyqt.sourceforge.net/Docs/PyQt5/Qt.html.
import os

from PyInstaller.utils.hooks import qt5_library_info

# Determine the name of all these modules by looking in the PyQt5 directory.
hiddenimports = []
for f in os.listdir(qt5_library_info.lib_dir):
    root, ext = os.path.splitext(os.path.basename(f))
    if root.startswith('Qt') and root != 'Qt':
        hiddenimports.append('PyQt5.' + root)
