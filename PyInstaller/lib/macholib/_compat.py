"""
2to3 compatibility routines
"""
import sys

if sys.version_info[0] == 3:
    def B(value):
        """
        Usage B("literal"), use this instead of b"literal" to ensure
        python <= 2.5 compatibility.
        """
        return value.encode("latin")
else:
    def B(value):
        return value

try:
    from __builtin__ import bytes
except ImportError:
    # Python 2.5 or earlier
    bytes = str
