#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_data_files

# Need to include modules in PyQt5.uic.widget-plugins, so they can be
# dynamically loaded by uic. They should both be included as separate
# (data-like) files, so they can be found by os.listdir and friends. However,
# this directory isn't a package, refer to it using the package (PyQt5.uic)
# followed by the subdirectory name (``widget-plugins/``).
datas = collect_data_files('PyQt5.uic', True, 'widget-plugins')
