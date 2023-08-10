#-----------------------------------------------------------------------------
# Copyright (c) 2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import sys
import pprint
import _imp  # A built-in

if sys.version_info < (3, 11):
    raise RuntimeError("Requires python >= 3.11!")

# Check that sys._stdlib_dir is set
if not sys._stdlib_dir:
    raise RuntimeError("sys._stdlib_dir is not set!")

# Frozen stdlib modules to test. Since these are frozen (by python itself), we do not need to specify them as hidden
# imports when this test script is frozen using PyInstaller.
frozen_stdlib_modules = sorted([name for name in _imp._frozen_module_names() if name in sys.stdlib_module_names])

output_data = [sys._stdlib_dir]  # First entry is sys._stdlib_dir
for module_name in frozen_stdlib_modules:
    print(f"Checking {module_name}...", file=sys.stderr)
    module = __import__(module_name)

    if not hasattr(module, '__file__'):
        raise RuntimeError(f"No __file__ attribute on {module_name}!")

    # Collect: module_name, __file__, filename and origname from __spec__.loaded_state
    loader_state = module.__spec__.loader_state
    entry = (
        module_name,
        module.__file__,
        loader_state.filename,
        loader_state.origname,
    )
    output_data.append(entry)

# Output: stdout or file
if len(sys.argv) > 1:
    with open(sys.argv[1], "w") as fp:
        pprint.pprint(output_data, stream=fp)
else:
    pprint.pprint(output_data)
