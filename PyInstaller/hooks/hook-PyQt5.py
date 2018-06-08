#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import os

from PyInstaller.utils.hooks import pyqt5_library_info, collect_system_data_files

hiddenimports = ['sip']

# Collect the ``qt.conf`` file.
datas = [x for x in
         collect_system_data_files(pyqt5_library_info.location['PrefixPath'],
                                   'PyQt5')
         if os.path.basename(x[0]) == 'qt.conf']
