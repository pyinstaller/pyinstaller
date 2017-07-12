# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2017, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import pytest

def test_ctypes_cdll_unknown_dll(pyi_builder,capfd):
    with pytest.raises(AssertionError):
        pyi_builder.test_source(
            """
            import ctypes
            ctypes.cdll.LoadLibrary('non-existing-2017')
            """)
    out, err = capfd.readouterr()
    assert "Failed to load dynlib/dll" in err
