#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import eval_statement

hiddenimports = ['PySide2.QtCore',
                 'PySide2.QtWidgets',
                 'PySide2.QtGui',
                 'PySide2.QtSvg']

if eval_statement("from PySide2 import Qwt5; print(hasattr(Qwt5, 'toNumpy'))"):
    hiddenimports.append("numpy")
if eval_statement("from PySide2 import Qwt5; print(hasattr(Qwt5, 'toNumeric'))"):
    hiddenimports.append("Numeric")
if eval_statement("from PySide2 import Qwt5; print(hasattr(Qwt5, 'toNumarray'))"):
    hiddenimports.append("numarray")
