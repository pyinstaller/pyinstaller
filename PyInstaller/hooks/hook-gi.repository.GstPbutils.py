#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Import hook for Gst(GStreamer) http://gstreamer.freedesktop.org/ introspected through
PyGobject https://wiki.gnome.org/PyGObject via the GObject Introspection middleware
layer https://wiki.gnome.org/Projects/GObjectIntrospection
"""
from PyInstaller.utils.hooks import get_gi_typelibs

binaries, datas, hiddenimports = get_gi_typelibs('GstPbutils', '1.0')
