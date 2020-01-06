#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = (collect_submodules('docutils.languages') +
                 collect_submodules('docutils.writers') +
                 collect_submodules('docutils.parsers.rst.languages') +
                 collect_submodules('docutils.parsers.rst.directives'))
datas = collect_data_files('docutils')
