#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# from stackoverflow.com/questions/55848884/[continue on nextline]
#google-cloud-firestore-doesnt-get-added-to-pyinstaller-build

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('grpc')
