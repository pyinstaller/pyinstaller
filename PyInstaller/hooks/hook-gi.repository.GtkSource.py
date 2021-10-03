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

from PyInstaller.utils.hooks.gi import (collect_glib_share_files, get_gi_typelibs)
from PyInstaller.utils.hooks import (get_hook_config, logger)


def hook(hook_api):
    module_versions = get_hook_config(hook_api, 'gi', 'module-versions')
    if module_versions:
        version = module_versions.get('GtkSource', '3.0')
    else:
        version = '3.0'
    logger.info(f'GtkSource version is {version}')

    binaries, datas, hiddenimports = get_gi_typelibs('GtkSource', version)

    datas += collect_glib_share_files(f'gtksourceview-{version}')
    hook_api.add_datas(datas)
    hook_api.add_binaries(binaries)
    hook_api.add_imports(*hiddenimports)
