#-----------------------------------------------------------------------------
# Copyright (c) 2014-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Certifi is a carefully curated collection of Root Certificates for
# validating the trustworthiness of SSL certificates while verifying
# the identity of TLS hosts.

# It has been extracted from the Requests project.

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('certifi')
