hiddenimports = ['sip', "PyQt4._qt"]

from hooks.hookutils import qt4_plugins_dir
pdir = qt4_plugins_dir()

datas = [
     (pdir + "/codecs/*.so",      "qt4_plugins/codecs"),
     (pdir + "/codecs/*.dll",     "qt4_plugins/codecs"),
     (pdir + "/codecs/*.dylib",   "qt4_plugins/codecs"),
]

