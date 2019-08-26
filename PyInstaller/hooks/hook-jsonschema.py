#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# This is needed to bundle draft3.json and draft4.json files that come
# with jsonschema module

from PyInstaller.utils.hooks import collect_data_files, copy_metadata
datas = collect_data_files('jsonschema')
datas += copy_metadata('jsonschema')
