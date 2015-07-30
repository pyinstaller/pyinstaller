"""
    pefile
"""
import sys

if sys.version_info[0] == 2:
    from .pefile_py2 import *
else:
    from .pefile_py3 import *
