#!/usr/bin/env python
import sys
from ctypes import *

def dummy(arg):
    if sys.platform == "linux2":
        tct = CDLL("testctypes.so")
    elif sys.platform == "darwin":
        tct = CDLL("testctypes.dylib")
    elif sys.platform == "win32":
        tct = CDLL("testctypes.dll")
    else:
        raise NotImplementedError
    return tct.dummy(arg)
