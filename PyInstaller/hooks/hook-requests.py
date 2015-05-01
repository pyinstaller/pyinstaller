#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# This is needed to bundle cacert.pem that comes with requests module

from PyInstaller.hooks.hookutils import collect_data_files
datas = collect_data_files('requests')
