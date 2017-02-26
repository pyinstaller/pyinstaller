from collections import deque
from ._compat import get_instructions
from urllib.request import pathname2url
from io import BytesIO, StringIO


def Bchr(value):
    return value


def enumerate_instructions(code_object):
    code_object_type = type(code_object)  # Type of all code objects.

    yield from get_instructions(code_object)

    # For each constant in this code object that is itself a code object,
    # parse this constant in the same manner.
    for constant in code_object.co_consts:
        if isinstance(constant, code_object_type):
            yield from enumerate_instructions(constant)
