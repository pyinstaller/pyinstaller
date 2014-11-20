#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Because this is PyQt4.uic, note the .. required in order to get back to the hooks subdirectory.
from PyInstaller.hooks.hookutils import collect_submodules, get_package_paths
from PyInstaller.compat import is_linux

import os


# Need to include modules in PyQt4.uic.widget-plugins, so they will be
# dnamically loaded by uic. They should both be included in the Python archive
# and as separate (data-like) files, so they can be found by os.listdir and
# friends. However, this directory isn't a package, so we can't collect
# submodules('PyQt4.uic.widget-plugins'). Instead, collect the parent directory
# for simplicity, since all the parent directory (uic) code will already be included.
hiddenimports = collect_submodules('PyQt4.uic')


# On Linux PyQt4.uic could use PyKDE4 package for some rendering.
if is_linux:
    hiddenimports += collect_submodules('PyKDE4') + ['PyQt4.QtSvg', 'PyQt4.QtXml']


# Likewise, a call to collect_data_files('PyQt4.uic.widget-plugins', True)
# would be very convenient, but again this isn't a package. Hand-code this
# to collect fewer files.
datas = []
pkg_base, pkg_dir = get_package_paths('PyQt4.uic')
widgets_dir = pkg_dir + '/widget-plugins/'


for f in os.listdir(widgets_dir):
    datas.append([widgets_dir + f, 'PyQt4/uic/widget-plugins'])
