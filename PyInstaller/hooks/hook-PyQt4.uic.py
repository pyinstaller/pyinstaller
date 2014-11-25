#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import os

# Because this is PyQt4.uic, note the fully qualified package name required in
# order to refer to hookutils.
from PyInstaller.hooks.hookutils import collect_submodules, collect_data_files
from PyInstaller.compat import is_linux

# On Linux PyQt4.uic could use PyKDE4 package for some rendering.
if is_linux:
    hiddenimports = collect_submodules('PyKDE4') + ['PyQt4.QtSvg', 'PyQt4.QtXml']

# Need to include modules in PyQt4.uic.widget-plugins, so they can be
# dynamically loaded by uic. They should both be included as separate
# (data-like) files, so they can be found by os.listdir and friends. However,
# this directory isn't a package, refer to it using the package (PyQt4.uic)
# followed by the subdirectory name (widget-plugins/).
datas = collect_data_files('PyQt4.uic', True, 'widget-plugins')
