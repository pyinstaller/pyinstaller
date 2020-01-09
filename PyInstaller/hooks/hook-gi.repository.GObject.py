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
Import hook for GObject https://developer.gnome.org/gobject/stable/ from the GLib
library https://wiki.gnome.org/Projects/GLib introspected through PyGobject https://wiki.gnome.org/PyGObject
via the GObject Introspection middleware layer https://wiki.gnome.org/Projects/GObjectIntrospection

Tested with GLib 2.44.1, PyGObject 3.16.2, and GObject Introspection 1.44.0 on Mac OS X 10.10 and
GLib 2.42.2, PyGObject 3.14.0, and GObject Introspection 1.42 on Windows 7
"""

from PyInstaller.utils.hooks import get_gi_typelibs

binaries, datas, hiddenimports = get_gi_typelibs('GObject', '2.0')

hiddenimports += ['gi._gobject']
