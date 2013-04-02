#!/usr/bin/env python

# Test resolving dynamic libraries loaded in Python code at runtime
# by Python module 'ctypes'

import ctypeslib
assert ctypeslib.dummy(42) == 42
