import sys
from PyInstaller.hooks.hookutils import qt4_menu_nib_dir

# In the new consolidated mode any PyQt depends on _qt
hiddenimports = ['sip', 'PyQt4._qt']

# For Qt to work on Mac OS X it is necessary include
# directory qt_menu.nib. This directory contains some
# resource files necessary to run PyQt app.
if sys.platform.startswith('darwin'):
    datas = [
        (qt4_menu_nib_dir(), ''),
    ]
