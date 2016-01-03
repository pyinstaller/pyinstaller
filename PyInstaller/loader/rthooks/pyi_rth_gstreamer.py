#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
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

os.environ['GST_PLUGIN_PATH'] = '{};{}'.format(
    sys._MEIPASS, os.path.join(sys._MEIPASS, 'gst-plugins'))

# Prevent permission issues on Windows
os.environ['GST_REGISTRY'] = os.path.join(sys._MEIPASS, 'registry.bin')

# Only use packaged plugins to prevent GStreamer from crashing when it finds
# plugins from another version which are installed system wide.
os.environ['GST_PLUGIN_SYSTEM_PATH'] = ''
