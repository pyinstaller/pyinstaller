from hooks import hookutils

hiddenimports = ["PyQt4.QtCore", "PyQt4.QtGui", "PyQt4.QtSvg"]

if hookutils.qwt_numpy_support():
    hiddenimports.append("numpy")
if hookutils.qwt_numeric_support():
    hiddenimports.append("Numeric")
if hookutils.qwt_numarray_support():
    hiddenimports.append("numarray")
