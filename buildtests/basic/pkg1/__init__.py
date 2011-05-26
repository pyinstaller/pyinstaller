""" pkg1 replaces itself with pkg2"""

__all__ = ["a", "b"]
import pkg2
import sys
sys.modules[__name__] = pkg2
from pkg2 import *
