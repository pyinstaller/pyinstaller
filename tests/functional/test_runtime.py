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

import pytest


def test_ctypes_cdll_unknown_dll(pyi_builder, capfd):
    with pytest.raises(pytest.fail.Exception, match="Running exe .* failed"):
        pyi_builder.test_source(
            """
            import ctypes
            ctypes.cdll.LoadLibrary('non-existing-2017')
            """
        )
    out, err = capfd.readouterr()
    assert "Failed to load dynlib/dll" in err
