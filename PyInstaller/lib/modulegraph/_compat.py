import sys
import textwrap

from collections import deque


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
    from StringIO import StringIO as BytesIO
    from StringIO import StringIO
    from urllib import pathname2url

    def Bchr(value):
        return chr(value)

    def enumerate_instructions(module_code_object):
        # Type of all code objects.
        code_object_type = type(module_code_object)
        code_objects = deque([module_code_object])
        current_objects = deque()
        while code_objects:
            code_object = code_objects.pop()
            for instruction in get_instructions(code_object):
                yield instruction
            # For each constant in this code object that is itself a code object,
            # parse this constant in the same manner.
            for constant in code_object.co_consts:
                if isinstance(constant, code_object_type):
                    current_objects.appendleft(constant)
            code_objects += current_objects
            current_objects = deque()
else:
    from urllib.request import pathname2url
    from io import BytesIO, StringIO

    def Bchr(value):
        return value

    # Python 2 cannot compile this
    exec(textwrap.dedent("""
        def enumerate_instructions(code_object):
            code_object_type = type(code_object)  # Type of all code objects.

            yield from get_instructions(code_object)

            # For each constant in this code object that is itself a code object,
            # parse this constant in the same manner.
            for constant in code_object.co_consts:
                if isinstance(constant, code_object_type):
                    yield from enumerate_instructions(constant)
        """))
