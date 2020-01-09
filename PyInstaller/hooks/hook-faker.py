#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules('faker.providers')
datas = (
    collect_data_files('text_unidecode') +  # noqa: W504
    collect_data_files('faker.providers', include_py_files=True)
)
