#!/usr/bin/env python
import sys
from ctypes import *

# Current working directory is set to dist directory for tests.

def dummy(arg):
    if sys.platform == "win32":
        tct = CDLL("..\\..\\ctypes\\testctypes-win.dll")
    elif sys.platform.startswith("darwin"):
        tct = CDLL("../../ctypes/testctypes.dylib")
    else:
        tct = CDLL("../../ctypes/testctypes.so")
    return tct.dummy(arg)
