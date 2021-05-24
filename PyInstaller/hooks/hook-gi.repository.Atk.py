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
from PyInstaller.utils.hooks import get_hook_config
from PyInstaller.utils.hooks.gi import collect_glib_translations, \
        get_gi_typelibs

binaries, datas, hiddenimports = get_gi_typelibs('Atk', '1.0')


def hook(hook_api):
    hook_datas = []
    lang_list = get_hook_config(hook_api, "gi", "languages")

    hook_datas += collect_glib_translations('atk10', lang_list)
    hook_api.add_datas(hook_datas)
