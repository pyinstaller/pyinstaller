#-----------------------------------------------------------------------------
# Copyright (c) 2016-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
python-wavefile: https://github.com/vokimon/python-wavefile
"""

from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = collect_dynamic_libs('wavefile')
