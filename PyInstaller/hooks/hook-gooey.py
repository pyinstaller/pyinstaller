#-----------------------------------------------------------------------------
# Copyright (c) 2018-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Gooey GUI carries some language and images for it's UI to function.
"""

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('gooey')
