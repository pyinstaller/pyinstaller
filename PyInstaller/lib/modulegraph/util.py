from __future__ import absolute_import

import os
import imp
import dis
import sys
import re
import marshal
import warnings

from collections import deque

try:
    unicode
except NameError:
    unicode = str


if sys.version_info[0] == 2:
    from StringIO import StringIO as BytesIO
    from StringIO import StringIO
    _cOrd = ord
else:
    from io import BytesIO, StringIO
    _cOrd = int


def imp_find_module(name, path=None):
    """
    same as imp.find_module, but handles dotted names
    """
    names = name.split('.')
    if path is not None:
        if isinstance(path, (str, unicode)):
            path = [os.path.realpath(path)]
    for name in names:
        result = imp.find_module(name, path)
        if result[0] is not None:
            result[0].close()
        path = [result[1]]
    return result

def _check_importer_for_path(name, path_item):
    try:
        importer = sys.path_importer_cache[path_item]
    except KeyError:
        for path_hook in sys.path_hooks:
            try:
                importer = path_hook(path_item)
                break
            except ImportError:
                pass
        else:
            importer = None
        sys.path_importer_cache.setdefault(path_item, importer)


    if importer is None:
        try:
            return imp.find_module(name, [path_item])
        except ImportError:
            return None
    return importer.find_module(name)

def imp_walk(name):
    """
    yields namepart, tuple_or_importer for each path item

    raise ImportError if a name can not be found.
    """
    warnings.warn("imp_walk will be removed in a future version", DeprecationWarning)

    if name in sys.builtin_module_names:
        yield name, (None, None, ("", "", imp.C_BUILTIN))
        return
    paths = sys.path
    res = None
    for namepart in name.split('.'):
        for path_item in paths:
            res = _check_importer_for_path(namepart, path_item)
            if hasattr(res, 'load_module'):
                if res.path.endswith('.py') or res.path.endswith('.pyw'):
                    fp = StringIO(res.get_source(namepart))
                    res = (fp, res.path, ('.py', 'rU', imp.PY_SOURCE))
                elif res.path.endswith('.pyc') or res.path.endswith('.pyo'):
                    co  = res.get_code(namepart)
                    fp = BytesIO(imp.get_magic() + b'\0\0\0\0' + marshal.dumps(co))
                    res = (fp, res.path, ('.pyc', 'rb', imp.PY_COMPILED))

                else:
                    res = (None, loader.path, (os.path.splitext(loader.path)[-1], 'rb', imp.C_EXTENSION))

                break
            elif isinstance(res, tuple):
                break
        else:
            break

        yield namepart, res
        paths = [os.path.join(path_item, namepart)]
    else:
        return

    raise ImportError('No module named %s' % (name,))


cookie_re = re.compile(b"coding[:=]\s*([-\w.]+)")
if sys.version_info[0] == 2:
    default_encoding = 'ascii'
else:
    default_encoding = 'utf-8'

def guess_encoding(fp):

    for i in range(2):
        ln = fp.readline()

        m = cookie_re.search(ln)
        if m is not None:
            return m.group(1).decode('ascii')

    return default_encoding


if sys.version_info >= (3,4):
    # In Python 3.4 or later the dis module has a much nicer interface
    # for working with bytecode, use that instead of peeking into the
    # raw bytecode.
    # Note: This nicely sidesteps any issues caused by moving from bytecode
    # to wordcode in python 3.6.
    get_instructions = dis.get_instructions

else:
    assert 'SET_LINENO' not in dis.opmap  # safety belt

    from .dis3 import get_instructions


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
