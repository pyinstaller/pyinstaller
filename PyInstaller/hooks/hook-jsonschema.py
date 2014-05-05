#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

#this is needed to bundle draft3.json and draft4.json files that come with jsonschema module
from PyInstaller.hooks.hookutils import collect_data_files
datas = collect_data_files('jsonschema')
