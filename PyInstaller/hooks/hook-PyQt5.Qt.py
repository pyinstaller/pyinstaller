#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# When PyQt5.Qt is imported it implies the import of all PyQt5 modules. See
# http://pyqt.sourceforge.net/Docs/PyQt5/Qt.html.
import os

from PyInstaller.utils.hooks import get_module_file_attribute

# Determine the name of all these modules by looking in the PyQt5 directory.
hiddenimports = []
for f in os.listdir(os.path.dirname(get_module_file_attribute('PyQt5'))):
    root, ext = os.path.splitext(os.path.basename(f))
    if root.startswith('Qt') and root != 'Qt':
        hiddenimports.append('PyQt5.' + root)
