#!/usr/bin/env python

# Test resolving dynamic libraries loaded in Python code at runtime
# by Python module 'ctypes'

try:
    import ctypes
except ImportError:
    # ctypes unavailable, testing ctypes support is pointless.
    sys.exit(0)

import ctypeslib
assert ctypeslib.dummy(42) == 42
