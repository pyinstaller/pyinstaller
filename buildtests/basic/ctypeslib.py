#!/usr/bin/env python
import sys
from ctypes import *

def dummy(arg):
    if sys.platform == "linux2":
        tct = CDLL("ctypes/testctypes.so")
    elif sys.platform[:6] == "darwin":
        tct = CDLL("ctypes/testctypes.dylib")
    elif sys.platform == "win32":
        tct = CDLL("ctypes\\testctypes.dll")
    else:
        raise NotImplementedError
    return tct.dummy(arg)
