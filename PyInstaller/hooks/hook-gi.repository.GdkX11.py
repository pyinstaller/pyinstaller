#-----------------------------------------------------------------------------
# Copyright (c) 2026, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks.gi import GiModuleInfo
from PyInstaller.utils.hooks import get_hook_config


def hook(hook_api):
    # Use the Gdk version from hook config, if available. If not, try using Gtk version from hook config, so that we
    # collect Gdk and Gtk of the same version.
    module_versions = get_hook_config(hook_api, 'gi', 'module-versions')
    if module_versions:
        version = module_versions.get('Gdk')
        if not version:
            version = module_versions.get('Gtk', '3.0')
    else:
        version = '3.0'

    module_info = GiModuleInfo('GdkX11', version)
    if module_info.available:
        binaries, datas, hiddenimports = module_info.collect_typelib_data()

        hook_api.add_datas(datas)
        hook_api.add_binaries(binaries)
        hook_api.add_imports(*hiddenimports)
