#-----------------------------------------------------------------------------
# Copyright (c) 2015-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os
import sys

os.environ['GTK_DATA_PREFIX'] = sys._MEIPASS
os.environ['GTK_EXE_PREFIX'] = sys._MEIPASS
os.environ['GTK_PATH'] = sys._MEIPASS

# Include these here, as GTK will import pango automatically
os.environ['PANGO_LIBDIR'] = sys._MEIPASS
os.environ['PANGO_SYSCONFDIR'] = os.path.join(sys._MEIPASS, 'etc') # TODO?
