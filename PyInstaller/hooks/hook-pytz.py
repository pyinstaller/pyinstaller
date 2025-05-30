#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_data_files

# On Linux pytz installed from distribution repository uses zoneinfo from /usr/share/zoneinfo/ and no data files might
# be collected.
datas = collect_data_files('pytz')

# pytz references pkg_resources in a fall-back codepath that should normally not be reached; add an exclude to prevent
# (now deprecated) pkg_resources from being pulled in the frozen application.
excludedimports = ['pkg_resources']
