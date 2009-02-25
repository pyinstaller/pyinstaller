hiddenimports = ['sip', 'PyQt4.QtCore', 'PyQt4._qt']

from hooks.hookutils import qt4_plugins_dir
pdir = qt4_plugins_dir()

datas = [
     (pdir + "/script/*.so",      "qt4_plugins/script"),
     (pdir + "/script/*.dll",     "qt4_plugins/script"),
     (pdir + "/script/*.dylib",   "qt4_plugins/script"),
]

