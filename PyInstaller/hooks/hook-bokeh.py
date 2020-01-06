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


from PyInstaller.utils.hooks import collect_data_files

# core/_templates/*
# server/static/**/*
# subcommands/*.py

datas = collect_data_files('bokeh.core') + \
        collect_data_files('bokeh.server') + \
        collect_data_files('bokeh.command.subcommands', include_py_files=True)
