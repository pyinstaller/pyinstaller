#-----------------------------------------------------------------------------
# Copyright (c) 2025, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller import compat
from PyInstaller.utils import hooks as hookutils


def pre_safe_import_module(api):
    if compat.is_linux:
        # See comment in the adjacent `hook-gi.py`.
        try:
            paths = hookutils.get_module_attribute(api.module_name, "__path__")
        except Exception:
            # Most likely `gi.overrides` cannot be imported.
            paths = []

        for path in paths:
            api.append_package_path(path)
