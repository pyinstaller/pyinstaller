hiddenimports = ['sip', 'PyQt4.QtCore', 'PyQt4._qt']

from PyInstaller.hooks.hookutils import qt4_plugins_binaries


def hook(mod):
    mod.binaries.extend(qt4_plugins_binaries('accessible'))
    mod.binaries.extend(qt4_plugins_binaries('iconengines'))
    mod.binaries.extend(qt4_plugins_binaries('imageformats'))
    mod.binaries.extend(qt4_plugins_binaries('inputmethods'))
    mod.binaries.extend(qt4_plugins_binaries('graphicssystems'))
    return mod
