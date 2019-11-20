#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Handlers are imported by a lazy-load proxy, based on a
# name-to-package mapping. Collect all handlers to ease packaging.
# If you want to reduce the size of your application, used
# `--exclude-module` to remove unused ones.
hiddenimports = [
    "passlib.handlers",
    "passlib.handlers.digests",
]
