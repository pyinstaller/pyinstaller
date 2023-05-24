# -----------------------------------------------------------------------------
# Copyright (c) 2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

# An importlib.util.LazyLoader test, based on example from
# https://docs.python.org/3/library/importlib.html#implementing-lazy-imports

import sys
import importlib.util


def lazy_import(name):
    spec = importlib.util.find_spec(name)
    loader = importlib.util.LazyLoader(spec.loader)
    spec.loader = loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


# Lazy-load the module...
lazy_module = lazy_import(sys.argv[1])
# ... and then trigger load by listing its contents
print(dir(lazy_module))
