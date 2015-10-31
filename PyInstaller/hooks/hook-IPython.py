#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Tested with IPython 4.0.0.

from PyInstaller.utils.hooks import collect_data_files

# Ignore 'matplotlib'. IPython contains support for matplotlib.
# Ignore GUI libraries. IPython supports integration with GUI frameworks.
# Assume that it will be imported by any other module when the user really
# uses it.
# TODO IPython uses 'tkinter' for clipboard acces on Linux/Unix. Ignore it conditionally.
excludedimports = ['gtk', 'matplotlib', 'PyQt4', 'PyQt5', 'PySide']

datas = collect_data_files('IPython')
