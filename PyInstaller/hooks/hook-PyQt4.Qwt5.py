#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.utils.hooks import eval_statement

hiddenimports = ["PyQt4.QtCore", "PyQt4.QtGui", "PyQt4.QtSvg"]

if eval_statement("from PyQt4 import Qwt5; print(hasattr(Qwt5, 'toNumpy'))"):
    hiddenimports.append("numpy")
if eval_statement("from PyQt4 import Qwt5; print(hasattr(Qwt5, 'toNumeric'))"):
    hiddenimports.append("Numeric")
if eval_statement("from PyQt4 import Qwt5; print(hasattr(Qwt5, 'toNumarray'))"):
    hiddenimports.append("numarray")
