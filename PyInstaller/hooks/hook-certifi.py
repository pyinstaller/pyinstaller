#-----------------------------------------------------------------------------
# Copyright (c) 2014-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Certifi is a carefully curated collection of Root Certificates for
# validating the trustworthiness of SSL certificates while verifying
# the identity of TLS hosts.

# It has been extracted from the Requests project.

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('certifi')
