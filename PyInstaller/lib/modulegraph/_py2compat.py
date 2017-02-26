from collections import deque
from ._compat import get_instructions
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