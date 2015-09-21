#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# GStreamer contains a lot of plugins. We need to collect them and bundle
# them wih the exe file.
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
Gst.init()
reg = Gst.Registry.get()
plug = reg.find_plugin('coreelements')
path = plug.get_filename()
print(os.path.dirname(path))
"""

plugin_path = exec_statement(statement)

pattern = os.path.join(plugin_path, 'libgst*')

binaries = [(f, os.path.join('gst_plugins')) for f in glob.glob(pattern)]

datas = get_typelibs('Gst', '1.0')
