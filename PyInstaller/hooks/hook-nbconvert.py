# -----------------------------------------------------------------------------
# Copyright (c) 2018-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas = collect_data_files('nbconvert')

# nbconvert uses entrypoints to read nbconvert.exporters from metadata file entry_points.txt.
datas += copy_metadata('nbconvert')
