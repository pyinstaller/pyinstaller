#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
"""
Import hook for Gst(GStreamer) http://gstreamer.freedesktop.org/ introspected through
PyGobject https://wiki.gnome.org/PyGObject via the GObject Introspection middleware
layer https://wiki.gnome.org/Projects/GObjectIntrospection

Tested with GStreamer 1.4.5, gst-python 1.4.0, PyGObject 3.16.2, and GObject Introspection 1.44.0 on Mac OS X 10.10 and
GStreamer 1.4.5, gst-python 1.4.0, PyGObject 3.14.0, and GObject Introspection 1.42 on Windows 7
"""


# GStreamer contains a lot of plugins. We need to collect them and bundle them wih the exe file.
# We also need to resolve binary dependencies of these GStreamer plugins.


import glob
import os
from PyInstaller.utils.hooks import exec_statement, get_typelibs

hiddenimports = ['gi.overrides.Gst', 'gi.repository.GObject', 'gi.repository.GModule', 'gi.repository.Gio']

statement = """
import os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
Gst.init(None)
reg = Gst.Registry.get()
plug = reg.find_plugin('coreelements')
path = plug.get_filename()
print(os.path.dirname(path))
"""

plugin_path = exec_statement(statement)

# Use a pattern of libgst* since all GStreamer plugins that conform to GStreamer standards start with libgst
# and we may have mixed plugin extensions, e.g., .so and .dylib.
pattern = os.path.join(plugin_path, 'libgst*')

binaries = [(f, os.path.join('gst_plugins')) for f in glob.glob(pattern)]

datas = get_typelibs('Gst', '1.0')
