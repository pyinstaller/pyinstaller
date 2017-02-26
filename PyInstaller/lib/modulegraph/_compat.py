import sys

if sys.version_info >= (3, 4):
    # In Python 3.4 or later the dis module has a much nicer interface
    # for working with bytecode, use that instead of peeking into the
    # raw bytecode.
    # Note: This nicely sidesteps any issues caused by moving from bytecode
    # to wordcode in python 3.6.
    from dis import get_instructions
else:
    from ._dis3 import get_instructions

# Must import at the end to avoid circular imports
if sys.version_info < (3, 0):
    from ._py2compat import enumerate_instructions, pathname2url, BytesIO, StringIO, Bchr
else:
    from ._py3compat import enumerate_instructions, pathname2url, BytesIO, StringIO, Bchr
