#-----------------------------------------------------------------------------
# Copyright (c) 2017-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Client library URL: https://googleapis.dev/python/cloudkms/latest/
# Import Example for client library:
# https://cloud.google.com/kms/docs/reference/libraries#client-libraries-install-python

from PyInstaller.utils.hooks import copy_metadata
datas = copy_metadata('google-cloud-kms')
