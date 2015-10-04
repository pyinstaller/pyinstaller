# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Utility functions related to analyzing/bundling dependencies.
"""

import ctypes
import dis
import io
import marshal
import os
import re
import zipfile

from ..lib.modulegraph import modulegraph

from .. import compat
from ..compat import is_darwin, is_unix, is_py2, BYTECODE_MAGIC, PY3_BASE_MODULES, \
    exec_python_rc
from .dylib import include_library
from .. import log as logging

logger = logging.getLogger(__name__)


# TODO find out if modules from base_library.zip could be somehow bundled into the .exe file.
def create_py3_base_library(libzip_filename, graph):
    """
    Package basic Python modules into .zip file. The .zip file with basic
    modules is necessary to have on PYTHONPATH for initializing libpython3
    in order to run the frozen executable with Python 3.
    """
    # TODO Replace this function with something better or something from standard Python library.
    # Helper functions.
    def _write_long(f, x):
        """
        Write a 32-bit int to a file in little-endian order.
        """
        f.write(bytes([x & 0xff,
                       (x >> 8) & 0xff,
                       (x >> 16) & 0xff,
                       (x >> 24) & 0xff]))

    # Construct regular expression for matching modules that should be bundled
    # into base_library.zip.
    regex_str = '|'.join(['(%s.*)' % x for x in PY3_BASE_MODULES])
    regex = re.compile(regex_str)

    try:
        # Remove .zip from previous run.
        if os.path.exists(libzip_filename):
            os.remove(libzip_filename)
        logger.debug('Adding python files to base_library.zip')
        # Class zipfile.PyZipFile is not suitable for PyInstaller needs.
        with zipfile.ZipFile(libzip_filename, mode='w') as zf:
            zf.debug = 3
            for mod in graph.flatten():
                if type(mod) in (modulegraph.SourceModule, modulegraph.Package):
                    # Bundling just required modules.
                    if regex.match(mod.identifier):
                        st = os.stat(mod.filename)
                        timestamp = int(st.st_mtime)
                        size = st.st_size & 0xFFFFFFFF
                        # Name inside a zip archive.
                        # TODO use .pyo suffix if optimize flag is enabled.
                        if type(mod) is modulegraph.Package:
                            new_name = mod.identifier.replace('.', os.sep) + os.sep + '__init__' + '.pyc'
                        else:
                            new_name = mod.identifier.replace('.', os.sep) + '.pyc'

                        # Write code to a file.
                        # This code is similar to py_compile.compile().
                        with io.BytesIO() as fc:
                            # Prepare all data in byte stream file-like object.
                            fc.write(BYTECODE_MAGIC)
                            _write_long(fc, timestamp)
                            _write_long(fc, size)
                            marshal.dump(mod.code, fc)
                            zf.writestr(new_name, fc.getvalue())

    except Exception as e:
        logger.error('base_library.zip could not be created!')
        raise


# This code does not work with Python 3 and is not used
# with modulegraph.
LOAD_CONST = dis.opmap['LOAD_CONST']
LOAD_GLOBAL = dis.opmap['LOAD_GLOBAL']
LOAD_NAME = dis.opmap['LOAD_NAME']
LOAD_ATTR = dis.opmap['LOAD_ATTR']
COND_OPS = set([dis.opmap['POP_JUMP_IF_TRUE'],
                dis.opmap['POP_JUMP_IF_FALSE'],
                dis.opmap['JUMP_IF_TRUE_OR_POP'],
                dis.opmap['JUMP_IF_FALSE_OR_POP'],
            ])
JUMP_FORWARD = dis.opmap['JUMP_FORWARD']
HASJREL = set(dis.hasjrel)
assert 'SET_LINENO' not in dis.opmap  # safty belt

if is_py2:
    _cOrd = ord
else:
    _cOrd = int

def pass1(code):
    """
    Parse the bytecode int a list of easy-usable tokens:
      (op, oparg, incondition, curline)
    """
    instrs = []
    i = 0
    n = len(code)
    # TODO reestablish line numbers or remove them at all
    curline = 0
    incondition = 0
    out = 0
    while i < n:
        if i >= out:
            incondition = 0
        c = code[i]
        i = i + 1
        op = _cOrd(c)
        if op >= dis.HAVE_ARGUMENT:
            oparg = _cOrd(code[i]) + _cOrd(code[i + 1]) * 256
            i = i + 2
        else:
            oparg = None
        if not incondition and op in COND_OPS:
            incondition = 1
            out = oparg
            if op in HASJREL:
                out += i
        elif incondition and op == JUMP_FORWARD:
            out = max(out, i + oparg)
        instrs.append((op, oparg, incondition, curline))
    return instrs


def scan_code_for_ctypes(co):
    instrs = pass1(co.co_code)
    warnings = []
    binaries = []

    for i in range(len(instrs)):
        # ctypes scanning requires a scope wider than one bytecode
        # instruction, so the code resides in a separate function
        # for clarity.
        ctypesb, ctypesw = scan_code_instruction_for_ctypes(co, instrs, i)
        binaries.extend(ctypesb)
        warnings.extend(ctypesw)

    for c in co.co_consts:
        if isinstance(c, type(co)):
            nested_binaries, nested_warnings = scan_code_for_ctypes(c)
            binaries.extend(nested_binaries)
            warnings.extend(nested_warnings)

    # If any of the libraries has been requested with anything
    # different then the bare filename, drop that entry and warn
    # the user - pyinstaller would need to patch the compiled pyc
    # file to make it work correctly!
    for binary in list(binaries):
        # 'binary' might be in some cases None. Some Python
        # modules might contain code like the following. For
        # example PyObjC.objc._bridgesupport contain code like
        # that.
        #     dll = ctypes.CDLL(None)
        if not binary:
            # None values has to be removed too.
            binaries.remove(binary)
        elif binary != os.path.basename(binary):
            # TODO make these warnings show up somewhere.
            warnings.append("W: ignoring %s - ctypes imports only supported using bare filenames" % binary)

    binaries = _resolveCtypesImports(binaries)
    return binaries, warnings


def scan_code_instruction_for_ctypes(co, instrs, i):
    """
    Detects ctypes dependencies, using reasonable heuristics that
    should cover most common ctypes usages; returns a tuple of two
    lists, one containing names of binaries detected as
    dependencies, the other containing warnings.
    """

    def _libFromConst(i):
        """Extracts library name from an expected LOAD_CONST instruction and
        appends it to local binaries list.
        """
        op, oparg, conditional, curline = instrs[i]
        if op == LOAD_CONST:
            soname = co.co_consts[oparg]
            binaries.add(soname)

    warnings = []
    binaries = set()

    op, oparg, conditional, curline = instrs[i]
    expected_ops = (LOAD_GLOBAL, LOAD_NAME)

    if op not in expected_ops:
        return [], []

    name = co.co_names[oparg]
    if name == "ctypes":
        # Guesses ctypes has been imported as `import ctypes` and
        # the members are accessed like: ctypes.CDLL("library.so")
        #
        #   LOAD_GLOBAL 0 (ctypes) <--- we "are" here right now
        #   LOAD_ATTR 1 (CDLL)
        #   LOAD_CONST 1 ('library.so')
        #
        # In this case "strip" the `ctypes` by advancing and expecting
        # `LOAD_ATTR` next.
        i += 1
        expected_ops = (LOAD_ATTR,)
        op, oparg, conditional, curline = instrs[i]
        if op not in expected_ops:
            return [], []
        name = co.co_names[oparg]

    if name in ("CDLL", "WinDLL", "OleDLL", "PyDLL"):
        # Guesses ctypes imports of this type: CDLL("library.so")
        #
        #   LOAD_GLOBAL 0 (CDLL) <--- we "are" here right now
        #   LOAD_CONST 1 ('library.so')
        _libFromConst(i + 1)

    elif name in ("cdll", "windll", "oledll", "pydll"):
        # Guesses ctypes imports of these types:
        #
        #  * cdll.library (only valid on Windows)
        #
        #     LOAD_GLOBAL 0 (cdll) <--- we "are" here right now
        #     LOAD_ATTR 1 (library)
        #
        #  * cdll.LoadLibrary("library.so")
        #
        #     LOAD_GLOBAL   0 (cdll) <--- we "are" here right now
        #     LOAD_ATTR     1 (LoadLibrary)
        #     LOAD_CONST    1 ('library.so')
        i += 1
        op, oparg, conditional, curline = instrs[i]
        if op == LOAD_ATTR:
            if co.co_names[oparg] == "LoadLibrary":
                # Second type, needs to fetch one more instruction
                _libFromConst(i + 1)
            else:
                # First type
                soname = co.co_names[oparg] + ".dll"
                binaries.add(soname)
    elif op == LOAD_ATTR and name in ("util", ):
        # Guesses ctypes imports of these types::
        #
        #  ctypes.util.find_library('gs')
        #
        #     LOAD_GLOBAL   0 (ctype)
        #     LOAD_ATTR     1 (util) <--- we "are" here right now
        #     LOAD_ATTR     1 (find_library)
        #     LOAD_CONST    1 ('gs')
        i += 1
        op, oparg, conditional, curline = instrs[i]
        if op == LOAD_ATTR:
            if co.co_names[oparg] == "find_library":
                i += 1
                op, oparg, conditional, curline = instrs[i]
                if op == LOAD_CONST:
                    libname = co.co_consts[oparg]
                    soname = ctypes.util.find_library(libname)
                    binaries.add(soname)
    return binaries, warnings


# TODO Reuse this code with modulegraph implementation
def _resolveCtypesImports(cbinaries):
    """
    Completes ctypes BINARY entries for modules with their full path.

    Input is a list of c-binary-names (as found by
    `scan_code_instruction_for_ctypes`). Output is a list of tuples
    ready to be appended to the ``binaries`` of a modules.

    This function temporarily extents PATH, LD_LIBRARY_PATH or
    DYLD_LIBRARY_PATH (depending on the plattform) by CONF['pathex']
    so shared libs will be search there, too.

    Example:
    >>> _resolveCtypesImports(['libgs.so'])
    [(libgs.so', ''/usr/lib/libgs.so', 'BINARY')]

    """
    from ctypes.util import find_library
    from ..config import CONF

    if is_unix:
        envvar = "LD_LIBRARY_PATH"
    elif is_darwin:
        envvar = "DYLD_LIBRARY_PATH"
    else:
        envvar = "PATH"

    def _setPaths():
        path = os.pathsep.join(CONF['pathex'])
        old = compat.getenv(envvar)
        if old is not None:
            path = os.pathsep.join((path, old))
        compat.setenv(envvar, path)
        return old

    def _restorePaths(old):
        if old is None:
            compat.unsetenv(envvar)
        else:
            compat.setenv(envvar, old)

    ret = []

    # Try to locate the shared library on disk. This is done by
    # executing ctypes.utile.find_library prepending ImportTracker's
    # local paths to library search paths, then replaces original values.
    old = _setPaths()
    for cbin in cbinaries:
        cpath = find_library(os.path.splitext(cbin)[0])
        if is_unix:
            # CAVEAT: find_library() is not the correct function. Ctype's
            # documentation says that it is meant to resolve only the filename
            # (as a *compiler* does) not the full path. Anyway, it works well
            # enough on Windows and Mac. On Linux, we need to implement
            # more code to find out the full path.
            if cpath is None:
                cpath = cbin
            # "man ld.so" says that we should first search LD_LIBRARY_PATH
            # and then the ldcache
            for d in compat.getenv(envvar, '').split(os.pathsep):
                if os.path.isfile(os.path.join(d, cpath)):
                    cpath = os.path.join(d, cpath)
                    break
            else:
                # TODO refactor this code to call 'ldconfig' only once - performance improvement.
                #      (it contains thousands of libraries)
                text = compat.exec_command("/sbin/ldconfig", "-p")
                # Skip first line of the library list because it is just
                # an informative line and might contain localized characters.
                # Example of first line with local cs_CZ.UTF-8:
                #
                #   V keši „/etc/ld.so.cache“ nalezeno knihoven: 2799
                #
                library_list = text.strip().splitlines()[1:]
                for L in library_list:
                    if cpath in L:
                        cpath = L.split("=>", 1)[1].strip()
                        assert os.path.isfile(cpath)
                        break
                else:
                    cpath = None
        if cpath is None:
            # Skip warning message if cbin (basename of library) is ignored.
            # This prevents messages like:
            # 'W: library kernel32.dll required via ctypes not found'
            if not include_library(cbin):
                continue
            logger.warn("library %s required via ctypes not found", cbin)
        else:
            if not include_library(cpath):
                continue
            ret.append((cbin, cpath, "BINARY"))
    _restorePaths(old)
    return ret


def get_path_to_egg(path):
    """
    Return the path to the python egg file, if the path points to a
    file inside a (or to an egg directly).
    Return `None` otherwise.
    """
    # This assumes, eggs are not nested.
    # TODO add support for unpacked eggs and for new .whl packages.
    lastpath = None  # marker to stop recursion
    while path and path != lastpath:
        if os.path.splitext(path)[1].lower() == (".egg"):
            if os.path.isfile(path) or os.path.isdir(path):
                return path
        lastpath = path
        path = os.path.dirname(path)
    return None


def is_path_to_egg(path):
    """
    Check if path points to a file inside a python egg file (or to an egg
       directly).
    """
    return get_path_to_egg(path) is not None


def is_real_extension_module(modname, filename):
    """
    Tries importing .so/.pyd Python extensions in a subprocess.

    Some Python libraries bundle DLLs with .so/.pyd suffix. e.g. libzmq.pyd
    in pyzmq. PyInstaller should not handle these "fake extensions" as real
    Python extensions.

    :param modname: Absolute module name.
    :param filename: Absolute path to the .so/.pyd file
    :return: True if module is importable and thus C extension, False otherwise
    """
    # Python 2 does not have module 'importlib.machinery'
    if is_py2:
        template = """
import imp
ext_tuple = ('.so', 'rb', 3)
fp = open('%(file)s', 'rb')
imp.load_module('%(module)s', fp, '%(file)s', ext_tuple)
        """
    else:
        template = """
from importlib.machinery import ExtensionFileLoader
loader = ExtensionFileLoader('%(module)s', '%(file)s')
loader.load_module('%(module)s')
"""

    code = template % {'module': modname, 'file': filename}
    exit_code = exec_python_rc('-c', code)
    return exit_code == 0
