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
Import hook for PyGObject https://wiki.gnome.org/PyGObject
"""

import os
import os.path

from PyInstaller.compat import is_win
from PyInstaller.utils.hooks import get_hook_config
from PyInstaller.utils.hooks.gi import \
    collect_glib_etc_files, collect_glib_share_files, collect_glib_translations, get_gi_typelibs

binaries, datas, hiddenimports = get_gi_typelibs('Gtk', '3.0')

datas += collect_glib_share_files('fontconfig')


def hook(hook_api):
    hook_datas = []

    icon_list = get_hook_config(hook_api, "gi", "icons")
    theme_list = get_hook_config(hook_api, "gi", "themes")
    lang_list = get_hook_config(hook_api, "gi", "languages")

    if icon_list is not None:
        for icon in icon_list:
            hook_datas += collect_glib_share_files(os.path.join("icons", icon))
    else:
        hook_datas += collect_glib_share_files('icons')

    if theme_list is not None:
        for theme in theme_list:
            hook_datas += collect_glib_share_files(os.path.join('themes', theme))
    else:
        hook_datas += collect_glib_share_files('themes')

    hook_datas += collect_glib_translations('gtk30', lang_list)

    hook_api.add_datas(hook_datas)


# these only seem to be required on Windows
if is_win:
    datas += collect_glib_etc_files('fonts')
    datas += collect_glib_etc_files('pango')
    datas += collect_glib_share_files('fonts')
