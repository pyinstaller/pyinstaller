#-----------------------------------------------------------------------------
# Copyright (c) 2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller import compat
from PyInstaller.utils.hooks.setuptools import setuptools_info


def pre_safe_import_module(api):
    # `distutils` was removed from from stdlib in python 3.12; if it is available, it is provided by `setuptools`.
    # Therefore, we need to create package/module alias entries, which prevent the setuptools._distutils` and its
    # submodules from being collected as top-level modules (as `distutils` and its submodules) in addition to being
    # collected as their "true" names.
    if compat.is_py312 and setuptools_info.distutils_vendored:
        for aliased_name, real_vendored_name in setuptools_info.get_distutils_aliases():
            api.add_alias_module(real_vendored_name, aliased_name)
