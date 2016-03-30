#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Tested with IPython 4.0.0.

from PyInstaller.compat import modname_tkinter, is_win, is_darwin
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Ignore 'matplotlib'. IPython contains support for matplotlib.
# Ignore GUI libraries. IPython supports integration with GUI frameworks.
# Assume that it will be imported by any other module when the user really
# uses it.
excludedimports = ['gtk', 'matplotlib', 'PyQt4', 'PyQt5', 'PySide']

# IPython uses 'tkinter' for clipboard access on Linux/Unix. Exclude it on Windows and OS X.
if is_win or is_darwin:
    excludedimports.append(modname_tkinter)


datas = collect_data_files('IPython')
