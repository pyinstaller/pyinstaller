#-----------------------------------------------------------------------------
# Copyright (c) 2014-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
from PyInstaller.utils.hooks import add_qt5_dependencies

hiddenimports, binaries, datas = add_qt5_dependencies(__file__)
