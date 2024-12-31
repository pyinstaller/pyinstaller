#-----------------------------------------------------------------------------
# Copyright (c) 2024, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller import log as logging
from PyInstaller.utils.hooks import tcl_tk

logger = logging.getLogger(__name__)


def pre_find_module_path(hook_api):
    if not tcl_tk.tcltk_info.available:
        logger.warning("tkinter installation is broken. It will be excluded from the application")
        hook_api.search_dirs = []
