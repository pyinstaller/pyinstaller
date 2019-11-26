# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
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
