#-----------------------------------------------------------------------------
# Copyright (c) 2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import logger, collect_submodules
from PyInstaller.utils.hooks.distutils import is_distutils_provided_by_setuptools


def pre_safe_import_module(api):
    if is_distutils_provided_by_setuptools():
        # If using setuptools-provided distutils (setuptools._distuils), mark distutils as runtime module. This
        # will inhibit collection of setuptools._distutils as distutils, which would result in duplication (as
        # we also need to collect setuptools._distutils under the original name to make the setuptools work in the
        # frozen application).
        #
        # The downside is, we need to mark the sub-modules as runtime modules as well, otherwise for example
        # "from distutils.version import LooseVersion" fails to pick up distutils and its runtime hook.
        logger.info('distutils: setuptools-provided copy of distutils detected')
        distutils_submodules = collect_submodules("setuptools._distutils")
        for module in distutils_submodules:
            api.add_runtime_module(module.replace("setuptools._distutils", "distutils"))
