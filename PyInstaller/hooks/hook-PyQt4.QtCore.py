hiddenimports = ['sip', "PyQt4._qt"]

from PyInstaller.hooks.hookutils import qt4_plugins_binaries


def hook(mod):
    mod.binaries.extend(qt4_plugins_binaries('codecs'))
    return mod
