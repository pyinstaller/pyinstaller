#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import sys


# Without this environment variable set to 'no' importing 'gst'
# causes 100% CPU load. (Tested on OSX.)
os.environ['GST_REGISTRY_FORK'] = 'no'


# Tested on OSX only.
os.environ['GST_PLUGIN_PATH'] = os.path.join(sys._MEIPASS, 'gst_plugins')
