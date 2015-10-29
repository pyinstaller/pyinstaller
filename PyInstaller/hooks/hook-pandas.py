#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Ignore 'IPython' and 'matplotlib'.
# Assume that if people are really using any n their application, they
# will also import it directly and PyInstaller will thus bundle them.
# 'pandas.util.clipboard' uses on Linux some gui libraries. Ignore them too.
excludedimports = ['IPython', 'matplotlib', 'gtk', 'PyQt4', 'PySide']
