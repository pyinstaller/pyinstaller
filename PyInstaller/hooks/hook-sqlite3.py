#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.hooks.hookutils import collect_submodules

hiddenimports = collect_submodules('sqlite3')
# Exclude the test submodule as this causes Tkinter to be included
hiddenimports = [x for x in hiddenimports if 'test.' not in x]
