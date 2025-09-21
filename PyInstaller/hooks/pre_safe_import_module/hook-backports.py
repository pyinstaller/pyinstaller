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

# This top-level namespace package might be provided by setuptools >= 71.0.0, which makes its vendored dependencies
# public by appending path to its `setuptools._vendored` directory to `sys.path`. The following shared
# pre-safe-import-module hook implementation checks whether this is the case, and, depending on situation, either
# sets up aliases to prevent duplicate collection, or extends the search paths.
from PyInstaller.utils.hooks.setuptools import pre_safe_import_module_for_top_level_namespace_packages \
    as pre_safe_import_module  # noqa: F401
