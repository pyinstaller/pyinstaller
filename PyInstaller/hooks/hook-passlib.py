#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Handlers are imported by a lazy-load proxy, based on a
# name-to-package mapping. Collect all handlers to ease packaging.
# If you want to reduce the size of your application, used
# `--exclude-module` to remove unused ones.
hiddenimports = [
    "passlib.handlers",
    "passlib.handlers.digests",
]
