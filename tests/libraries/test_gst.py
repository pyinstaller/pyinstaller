#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Test for GStreamer Python bindings.


# gst module is trying to load some plugins
# and loading plugins should fail when they are not bundled.


import sys
import gst


reg = gst.registry_get_default()
plug = reg.find_plugin('coreelements')
pth = plug.get_filename()
print('coreelements plugin: %s' % pth)


if not pth.startswith(sys._MEIPASS):
    raise SystemExit('GStreamer coreelements plugin not loaded from MEIPASS/gst_plugins.')
