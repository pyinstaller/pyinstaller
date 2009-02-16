#!/usr/bin/env python

from ctypes import *

def dummy(arg):
    tct = CDLL("testctypes.dylib")
    return tct.dummy(arg)
