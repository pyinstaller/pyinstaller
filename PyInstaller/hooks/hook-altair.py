# -----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

"""
Hook for https://altair-viz.github.io/index.html
tested for altair version 4.1.0
"""

from PyInstaller.utils.hooks import collect_data_files


# include the json schema files

# the collect_data_files includes .pyo files,
# even though include_py_files is set to False.

datas = [(src, dest) for (src, dest)
         in collect_data_files('altair', include_py_files=False)
         if src.endswith('.json')]
