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

import fnmatch
from PyInstaller.utils.hooks.setuptools import setuptools_info

# Use cached data files list from setuptools_info, and extract relevant bits (to avoid having to call another
# `collect_data_files` and import `setuptools` in isolated process).
datas = [(src_name, dest_name) for src_name, dest_name in setuptools_info.vendored_data
         if fnmatch.fnmatch(src_name, "**/setuptools/_vendor/jaraco/text/*")]
