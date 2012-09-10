# Qt4 plugins are bundled as data files (see hooks/hook-PyQt4*),
# within a "qt4_plugins" directory.
# We add a runtime hook to tell Qt4 where to find them.

import os
import sys

d = "qt4_plugins"
d = os.path.join(sys._MEIPASS, d)


# We remove QT_PLUGIN_PATH variable, because we want Qt4 to load
# plugins only from one path.
if 'QT_PLUGIN_PATH' in os.environ:
    del os.environ['QT_PLUGIN_PATH']

# Check if the user has a 'pyi_rth_user_config' module with a valid
# 'PYQT_API_VERSION' constant defined to override the default PyQt API version.
try:
    from pyi_rth_user_config import PYQT_API_VERSION
    if PYQT_API_VERSION in [1, 2]:
        import sip
        for class_name in [
            'QDate', 'QDateTime', 'QString', 'QTextStream', 'QTime', 'QUrl',
            'QVariant',
        ]:
            sip.setapi(class_name, PYQT_API_VERSION)
except ImportError:
    # 'pyi_rth_user_config.PYQT_API_VERSION' doesn't exist: default behaviour
    pass

# We cannot use QT_PLUGIN_PATH here, because it would not work when
# PyQt4 is compiled with a different CRT from Python (eg: it happens
# with Riverbank's GPL package).
from PyQt4.QtCore import QCoreApplication
# We set "qt4_plugins" as only one path for Qt4 plugins
QCoreApplication.setLibraryPaths([os.path.abspath(d)])
