#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Import hook for PyEnchant.

Tested with PyEnchatn 1.6.6.
"""

import os
import sys

from PyInstaller.compat import is_darwin
from PyInstaller.utils.hooks.hookutils import exec_statement, collect_data_files, \
    collect_dynamic_libs, eval_script


# TODO Add Linux support
# Collect first all files that were installed directly into pyenchant
# package directory and this includes:
# - Windows: libenchat-1.dll, libenchat_ispell.dll, libenchant_myspell.dll, other
#            dependent dlls and dictionaries for several languages (de, en, fr)
# - Mac OS X: usually libenchant.dylib and several dictionaries when installed via pip.
binaries = collect_dynamic_libs('enchant')
datas = collect_data_files('enchant')


# On OS X try to find files from Homebrew or Macports environments.
if is_darwin:
    libenchant = exec_statement("""
from enchant._enchant import e
print(e._name)
""").strip()

    # Check libenchant was not installed via pip but is somewhere on disk.
    if not libenchant.startswith(sys.prefix):
        # 'libenchant' was not installed via pip - append it to 'binaries'.
        binaries.append((libenchant, 'enchant'))

        # Collect enchant backends from Macports.
        # Collect all available dictionaries from Macports.

#
#     for f in files:  # Put the enchant library in lib/ so the enchant plugins can find it
#         binaries.append((f, 'lib'))
#     files = exec_statement("""
# from enchant import Broker
# for provider in Broker().describe():
#     print(provider.file)""").strip().split()
#     for f in files:  # Put enchant plugins in lib/enchant/ so the enchant library can find them
#         binaries.append((f, os.path.join('lib', 'enchant')))
#
#     datas = []
#     files = collect_data_files('enchant')  # Only works if pyenchant is installed via pip
#     for file in files:
#         if 'share' in file[0] and not file[0].endswith('.zip') and 'man' not in file[0]:
#             datas.append((file[0], os.sep.join(file[1].split(os.sep)[1:])))
