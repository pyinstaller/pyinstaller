#-----------------------------------------------------------------------------
# Copyright (c) 2014-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# This is needed to bundle cacerts.txt that comes with httplib2 module

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('httplib2')
