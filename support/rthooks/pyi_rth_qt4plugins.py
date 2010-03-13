# Qt4 plugins are bundled as data files (see hooks/hook-PyQt4*),
# within a "qt4_plugins" directory.
# We add a runtime hook to tell Qt4 where to find them.
import os
d = "qt4_plugins"
if "_MEIPASS2" in os.environ:
    d = os.path.join(os.environ["_MEIPASS2"], d)
else:
    d = os.path.join(os.path.dirname(sys.argv[0]), d)
    
# We cannot use QT_PLUGIN_PATH here, because it would not work when
# PyQt4 is compiled with a different CRT from Python (eg: it happens
# with Riverbank's GPL package).
from PyQt4.QtCore import QCoreApplication
QCoreApplication.addLibraryPath(os.path.abspath(d))
