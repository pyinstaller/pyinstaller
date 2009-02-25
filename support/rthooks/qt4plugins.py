# Qt4 plugins are bundled as data files (see hooks/hook-PyQt4*),
# within a "qt4_plugins" directory.
# We add a runtime hook to tell Qt4 where to find them,
# through an environment variable.
import os
d = "qt4_plugins"
if "_MEIPASS2" in os.environ:
    d = os.path.join(os.environ["_MEIPASS2"], d)
os.environ["QT_PLUGIN_PATH"] = d + os.pathsep + os.environ.get("QT_PLUGIN_PATH", "")

