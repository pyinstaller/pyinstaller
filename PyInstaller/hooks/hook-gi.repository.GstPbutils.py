#-----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
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
"""
from PyInstaller.utils.hooks import get_gi_typelibs

binaries, datas, hiddenimports = get_gi_typelibs('GstPbutils', '1.0')
