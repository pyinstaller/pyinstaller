#!/usr/bin/env python
import sys
from ctypes import *

def dummy(arg):
    if (sys.platform.startswith("linux") or
        sys.platform.startswith("sun") or
        sys.platform.startswith("aix")):
        tct = CDLL("ctypes/testctypes.so")
    elif sys.platform.startswith("darwin"):
        tct = CDLL("ctypes/testctypes.dylib")
    elif sys.platform == "win32":
        tct = CDLL("ctypes\\testctypes.dll")
    else:
        raise NotImplementedError
    return tct.dummy(arg)
