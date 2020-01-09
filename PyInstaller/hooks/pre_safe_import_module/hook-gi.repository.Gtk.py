#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


def pre_safe_import_module(api):
    # PyGObject modules loaded through the gi repository are marked as
    # MissingModules by modulegraph so we convert them to
    # RuntimeModules so their hooks are loaded and run.
    api.add_runtime_module(api.module_name)
