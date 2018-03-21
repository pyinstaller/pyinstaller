#-----------------------------------------------------------------------------
# Copyright (c) 2016-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
accessible_output2: http://hg.q-continuum.net/accessible_output2
"""

from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = collect_dynamic_libs('accessible_output2')
