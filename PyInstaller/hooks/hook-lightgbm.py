# -----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------
#
# A fast, distributed, high performance gradient boosting 
# (GBT, GBDT, GBRT, GBM or MART) framework based on decision 
# tree algorithms, used for ranking, classification and
# many other machine learning tasks.
#
# https://github.com/microsoft/LightGBM
#
# Tested with:
# Tested on Windows 10 & macOS 10.14 with Python 3.7.5

from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = collect_dynamic_libs('lightgbm')
binaries += collect_dynamic_libs('sklearn')
binaries += collect_dynamic_libs('scipy')
