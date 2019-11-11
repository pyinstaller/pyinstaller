#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# hook for google firestore: https://github.com/MartinSahlen/cloud-functions-python/issues/56

from PyInstaller.utils.hooks import copy_metadata

datas = copy_metadata('google-cloud-core')
datas += copy_metadata('google-cloud-firestore')
datas += copy_metadata('google-api-core')