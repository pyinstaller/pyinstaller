#-----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os

from PyInstaller.utils.hooks import (
    get_module_attribute, is_module_satisfies, qt_menu_nib_dir, get_module_file_attribute,
    collect_data_files)
from PyInstaller.compat import getsitepackages, is_darwin, is_win

# On Windows system PATH has to be extended to point to the PySide2 directory.
# The PySide directory contains Qt dlls. We need to avoid including different
# version of Qt libraries when there is installed another application (e.g. QtCreator)
if is_win:
    from PyInstaller.utils.win32.winutils import extend_system_path

    extend_system_path([os.path.join(x, 'PySide2') for x in getsitepackages()])
    extend_system_path([os.path.join(os.path.dirname(get_module_file_attribute('PySide2')),
                                     'Qt', 'bin')])

# FIXME: this should not be needed
hiddenimports = ['numpy.core.multiarray']

# TODO: check if this is needed
# Collect just the qt.conf file.
datas = [x for x in collect_data_files('PySide2', False, os.path.join('Qt', 'bin')) if
         x[0].endswith('qt.conf')]
