hiddenimports = ['sip', 'PyQt4.QtGui', 'PyQt4._qt']

from hooks.hookutils import qt4_phonon_plugins_dir
pdir = qt4_phonon_plugins_dir()

datas = [
     (pdir + "/phonon_backend/*.so",      "qt4_plugins/phonon_backend"),
     (pdir + "/phonon_backend/*.dll",     "qt4_plugins/phonon_backend"),
     (pdir + "/phonon_backend/*.dylib",   "qt4_plugins/phonon_backend"),
]

