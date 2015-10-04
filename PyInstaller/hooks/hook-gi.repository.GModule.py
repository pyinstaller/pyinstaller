#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
"""
Import hook for GModule https://developer.gnome.org/glib/stable/glib-Dynamic-Loading-of-Modules.html from the GLib
library https://wiki.gnome.org/Projects/GLib introspected through PyGobject https://wiki.gnome.org/PyGObject
via the GObject Introspection middleware layer https://wiki.gnome.org/Projects/GObjectIntrospection

Tested with GLib 2.44.1, PyGObject 3.16.2, and GObject Introspection 1.44.0 on Mac OS X 10.10 and
GLib 2.42.2, PyGObject 3.14.0, and GObject Introspection 1.42 on Windows 7
"""

from PyInstaller.utils.hooks import get_typelibs

hiddenimports = ['gi.overrides.GModule']

datas = get_typelibs('GModule', '2.0')
