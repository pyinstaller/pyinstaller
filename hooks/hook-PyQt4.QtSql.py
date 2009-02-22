hiddenimports = ['sip', 'PyQt4.QtCore', 'PyQt4.QtGui', 'PyQt4._qt']

from hooks.hookutils import qt4_plugins_dir
pdir = qt4_plugins_dir()

datas = [
     (pdir + "/sqldrivers/*.so",      "qt4_plugins/sqldrivers"),
     (pdir + "/sqldrivers/*.dll",     "qt4_plugins/sqldrivers"),
     (pdir + "/sqldrivers/*.dylib",   "qt4_plugins/sqldrivers"),
]

