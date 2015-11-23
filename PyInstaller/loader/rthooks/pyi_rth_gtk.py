import os
import sys

os.environ['GTK_DATA_PREFIX'] = sys._MEIPASS
os.environ['GTK_EXE_PREFIX'] = sys._MEIPASS
os.environ['GTK_PATH'] = sys._MEIPASS

# Include these here, as GTK will import pango automatically
os.environ['PANGO_LIBDIR'] = sys._MEIPASS
os.environ['PANGO_SYSCONFDIR'] = os.path.join(sys._MEIPASS, 'etc') # TODO?
