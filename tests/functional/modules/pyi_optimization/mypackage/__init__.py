# -----------------------------------------------------------------------------
# Copyright (c) 2024, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

# A test package for use with `pyi_optimization.py` test program.

# Module's docstring
"""Test package."""

# Check if __debug__ is set
has_debug = __debug__

# Check if assert works
has_assert = True
try:
    assert False
    has_assert = False
except Exception:
    pass


# Function with a docstring
def test_function():
    """Test function."""
    pass
