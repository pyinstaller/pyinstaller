hiddenimports = ['sip', 'PyQt4.QtCore', 'PyQt4._qt']

from hooks.hookutils import qt4_plugins_dir
pdir = qt4_plugins_dir()

datas = [
     (pdir + "/imageformats/*.so",      "qt4_plugins/imageformats"),
     (pdir + "/imageformats/*.dll",     "qt4_plugins/imageformats"),
     (pdir + "/imageformats/*.dylib",   "qt4_plugins/imageformats"),

     (pdir + "/iconengines/*.so",       "qt4_plugins/iconengines"),
     (pdir + "/iconengines/*.dll",      "qt4_plugins/iconengines"),
     (pdir + "/iconengines/*.dylib",    "qt4_plugins/iconengines"),

     (pdir + "/accessible/*.so",        "qt4_plugins/accessible"),
     (pdir + "/accessible/*.dll",       "qt4_plugins/accessible"),
     (pdir + "/accessible/*.dylib",     "qt4_plugins/accessible"),
]

