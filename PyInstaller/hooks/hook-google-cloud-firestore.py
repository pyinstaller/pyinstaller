#tsd 5-1-19
# from https://github.com/MartinSahlen/cloud-functions-python/issues/56
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import copy_metadata, copytree, get_package_dir
datas += copy_metadata('google-cloud-firestore')
datas += copy_metadata('google_cloud_firestore')  #alt

hiddenimports += ['google-cloud-firestore_v1']
#pythonhosted.org/pyinstaller/hooks.html#understanding-pyinstaller-hooks
#get_package_dir returns tuple (where pkg stored, abs path to pkg)
pkg_dir = '/usr/local/opt/python-3.7.0/lib/python3.7/site-packages/google/cloud/firestore_v1'

datas += (pkg_dir, 'google-cloud-firestore')
