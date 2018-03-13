#-----------------------------------------------------------------------------
# Copyright (c) 2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Fixes issue #2978 with pandas version 0.21
(Pandas missing `pandas._libs.tslibs.timedeltas.so`)
"""


hiddenimports = ['pandas._libs.tslibs.timedeltas']
