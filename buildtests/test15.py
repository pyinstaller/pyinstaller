#!/usr/bin/env python

try:
    import ctypes
except ImportError:
    # ctypes unavailable, testing ctypes support is pointless.
    sys.exit(0)

import test15a
assert test15a.dummy(42) == 42
