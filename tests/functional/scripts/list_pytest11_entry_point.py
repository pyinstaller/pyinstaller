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
Print all modules exporting the entry point 'pytest11'.
"""

import pkg_resources

plugins = sorted(i.module_name for i in pkg_resources.iter_entry_points("pytest11"))

print("\n".join(plugins))
