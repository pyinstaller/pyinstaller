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

# This script checks for availability of features/flags that are turned off at higher optimization levels.

import sys
import json

# Test package that implements similar checks.
import mypackage

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


# Collect results from both entry-point script and test package.
results = {
    "sys.flags.optimize": sys.flags.optimize,
    "script": {
        "has_debug": has_debug,
        "has_assert": has_assert,
        "function_has_doc": test_function.__doc__ is not None,
    },
    "module": {
        "has_debug": mypackage.has_debug,
        "has_assert": mypackage.has_assert,
        "module_has_doc": mypackage.__doc__ is not None,
        "function_has_doc": mypackage.test_function.__doc__ is not None,
    }
}

# Write to JSON file, or dump to stdout
if len(sys.argv) > 1:
    with open(sys.argv[1], "w") as fp:
        json.dump(results, fp, indent=2)
else:
    json.dump(results, sys.stdout, indent=2)
