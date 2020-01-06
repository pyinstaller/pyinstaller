#-----------------------------------------------------------------------------
# Copyright (c) 2015-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
#
# Boto3, the next version of Boto, is now stable and recommended for general
# use.
#
# Boto is an integrated interface to current and future infrastructural
# services offered by Amazon Web Services.
#
# http://boto.readthedocs.org/en/latest/
#
# Tested with boto 2.38.0

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('boto')
