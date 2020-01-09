#-----------------------------------------------------------------------------
# Copyright (c) 2019-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
# hook for https://github.com/openstack/sqlalchemy-migrate
# Since v0.12.0 importing migrate requires metadata to resolve __version__
# attribute

from PyInstaller.utils.hooks import copy_metadata, is_module_satisfies

if is_module_satisfies('sqlalchemy-migrate >= 0.12.0'):
    datas = copy_metadata('sqlalchemy-migrate')
