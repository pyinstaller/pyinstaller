#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


def pre_safe_import_module(api):
    api.add_alias_module('pyi_testmod_submodule_from_aliased_pkg', 'alias_name')
