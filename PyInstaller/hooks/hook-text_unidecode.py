# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

"""
text-unidecode:
https://github.com/kmike/text-unidecode/
"""

import os
from PyInstaller.utils.hooks import get_package_paths


package_path = get_package_paths("text_unidecode")
data_bin_path = os.path.join(package_path[1], "data.bin")

if os.path.exists(data_bin_path):
    datas = [(data_bin_path, 'text_unidecode')]
