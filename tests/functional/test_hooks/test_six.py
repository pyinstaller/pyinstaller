# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.tests import requires


@requires('six >= 1.0')
def test_six_moves(pyi_builder):
    pyi_builder.test_source("""
        from six.moves import UserList
        UserList
        """)


# Run the same test a second time to trigger errors like
#   Target module "six.moves.urllib" already imported as "AliasNode(…)"
# caused by PyiModuleGraph being cached in a insufficient way.
@requires('six >= 1.0')
def test_six_moves_2nd_run(pyi_builder):
    return test_six_moves(pyi_builder)
