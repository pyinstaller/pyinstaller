from PyInstaller.hooks.hookutils import eval_statement

hiddenimports = ["PyQt4.QtCore", "PyQt4.QtGui", "PyQt4.QtSvg"]

if eval_statement("from PyQt4 import Qwt5; print hasattr(Qwt5, 'toNumpy')"):
    hiddenimports.append("numpy")
if eval_statement("from PyQt4 import Qwt5; print hasattr(Qwt5, 'toNumeric')"):
    hiddenimports.append("Numeric")
if eval_statement("from PyQt4 import Qwt5; print hasattr(Qwt5, 'toNumarray')"):
    hiddenimports.append("numarray")
