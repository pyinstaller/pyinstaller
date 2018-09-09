#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
"""
Import hook for PyGObject's "gi.repository.Champlain" package.
"""

from PyInstaller.utils.hooks import get_gi_typelibs

binaries, datas, hiddenimports = get_gi_typelibs('Champlain', '0.12')
