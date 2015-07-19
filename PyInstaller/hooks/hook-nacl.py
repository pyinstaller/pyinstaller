#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Tested with PyNaCl 0.3.0 on Mac OS X.


import os.path
import glob
from PyInstaller.hooks.hookutils import collect_data_files, get_module_file_attribute
from PyInstaller.hooks.hookutils import PY_EXTENSION_SUFFIXES


datas = collect_data_files('nacl')

# Include the cffi extensions as binaries in a subfolder named like the package.
binaries = []
nacl_dir = os.path.dirname(get_module_file_attribute('nacl'))
for ext in PY_EXTENSION_SUFFIXES:
    ffimods = glob.glob(os.path.join(nacl_dir, '_lib', '*_cffi_*%s*' % ext))
    for f in ffimods:
        name = os.path.join('nacl', '_lib', os.path.basename(f))
        binaries.append((name, f))
