#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Import hook for the GLib library https://wiki.gnome.org/Projects/GLib introspected through
PyGobject https://wiki.gnome.org/PyGObject via the GObject Introspection middleware layer
https://wiki.gnome.org/Projects/GObjectIntrospection

Tested with GLib 2.44.1, PyGObject 3.16.2, and GObject Introspection 1.44.0 on Mac OS 10.10 and
GLib 2.42.2, PyGObject 3.14.0, and GObject Introspection 1.42 on Windows 7.
"""

import glob
import os

from PyInstaller.compat import is_win
from PyInstaller.utils.hooks import get_hook_config
from PyInstaller.utils.hooks.gi import \
    collect_glib_share_files, collect_glib_translations, get_gi_libdir, get_gi_typelibs

binaries, datas, hiddenimports = get_gi_typelibs('GLib', '2.0')


def hook(hook_api):
    hook_datas = []
    lang_list = get_hook_config(hook_api, "gi", "languages")

    hook_datas += collect_glib_translations('glib20', lang_list)
    hook_api.add_datas(hook_datas)


datas += collect_glib_share_files('glib-2.0', 'schemas')

# On Windows, glib needs a spawn helper for g_spawn* API
if is_win:
    libdir = get_gi_libdir('GLib', '2.0')
    pattern = os.path.join(libdir, 'gspawn-*-helper*.exe')
    for f in glob.glob(pattern):
        binaries.append((f, '.'))
