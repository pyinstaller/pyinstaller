#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []

# On Windows in Python 3.4 'sqlite3' package might contain tests.
# these tests are not necessary for the final executable.
for mod in collect_submodules('sqlite3'):
    if not mod.startswith('sqlite3.test'):
        hiddenimports.append(mod)

