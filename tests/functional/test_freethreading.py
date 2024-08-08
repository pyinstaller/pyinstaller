#-----------------------------------------------------------------------------
# Copyright (c) 2024, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import pytest

from PyInstaller.compat import is_nogil

# All tests in this file require freethreading-enabled python build (i.e., built with Py_GIL_DISABLED).
pytestmark = pytest.mark.skipif(not is_nogil, reason="Requires freethreading-enabled python build.")


# Test that GIL can be explicitly disabled or re-enabled via `X gil=0` and `X gil=1` python option.
@pytest.mark.parametrize('gil_value', [0, 1], ids=['enabled', 'disabled'])
def test_freethreading_explicit_gil_setting(pyi_builder, gil_value):
    pyi_builder.test_source(
        """
        import sys

        # Expected status is passed via first argument, as 0/1 integer.
        expected_status = bool(int(sys.argv[1]))

        status = sys._is_gil_enabled()
        print("GIL status: {status}")
        if status != expected_status:
            raise ValueError(f"Unexpected GIL status: {status}; expected {expected_status}")
        """,
        pyi_args=['--python-option', f'X gil={gil_value}'],
        app_args=[str(gil_value)],
    )
