#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# hook for https://pypi.org/project/Scrapy/
# https://stackoverflow.com/questions/49085970/no-such-file-or-directory-error-using-pyinstaller-and-scrapy

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files('scrapy')

hiddenimports = (
    collect_submodules('scrapy') +
    collect_submodules('scrapy.pipelines') +
    collect_submodules('scrapy.utils') +
    collect_submodules('scrapy.extensions')
)
