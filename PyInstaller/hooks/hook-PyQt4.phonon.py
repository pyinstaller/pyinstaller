import os.path

hiddenimports = ['sip', 'PyQt4.QtGui', 'PyQt4._qt']

from PyInstaller.hooks.hookutils import qt4_phonon_plugins_dir
pdir = qt4_phonon_plugins_dir()

_dest_dir = os.path.join("qt4_plugins", "phonon_backend")
datas = [
     (os.path.join(pdir, "phonon_backend", "*.so"),    _dest_dir),
     (os.path.join(pdir, "phonon_backend", "*.dll"),   _dest_dir),
     (os.path.join(pdir, "phonon_backend", "*.dylib"), _dest_dir),
]
