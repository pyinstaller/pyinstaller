#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Scan the code object for imports, __all__ and wierd stuff
"""


import dis
import os

from PyInstaller import compat
from PyInstaller.compat import ctypes

from PyInstaller.compat import is_unix, is_darwin, is_py25, is_py27

import PyInstaller.depend.utils
import PyInstaller.log as logging


logger = logging.getLogger(__name__)


IMPORT_NAME = dis.opname.index('IMPORT_NAME')
IMPORT_FROM = dis.opname.index('IMPORT_FROM')
try:
    IMPORT_STAR = dis.opname.index('IMPORT_STAR')
except:
    IMPORT_STAR = None
STORE_NAME = dis.opname.index('STORE_NAME')
STORE_FAST = dis.opname.index('STORE_FAST')
STORE_GLOBAL = dis.opname.index('STORE_GLOBAL')
try:
    STORE_MAP = dis.opname.index('STORE_MAP')
except:
    STORE_MAP = None
LOAD_GLOBAL = dis.opname.index('LOAD_GLOBAL')
LOAD_ATTR = dis.opname.index('LOAD_ATTR')
LOAD_NAME = dis.opname.index('LOAD_NAME')
EXEC_STMT = dis.opname.index('EXEC_STMT')
try:
    SET_LINENO = dis.opname.index('SET_LINENO')
except ValueError:
    SET_LINENO = None
BUILD_LIST = dis.opname.index('BUILD_LIST')
LOAD_CONST = dis.opname.index('LOAD_CONST')
if is_py25:
    LOAD_CONST_level = LOAD_CONST
else:
    LOAD_CONST_level = None
if is_py27:
    COND_OPS = set([dis.opname.index('POP_JUMP_IF_TRUE'),
                    dis.opname.index('POP_JUMP_IF_FALSE'),
                    dis.opname.index('JUMP_IF_TRUE_OR_POP'),
                    dis.opname.index('JUMP_IF_FALSE_OR_POP'),
                    ])
else:
    COND_OPS = set([dis.opname.index('JUMP_IF_FALSE'),
                    dis.opname.index('JUMP_IF_TRUE'),
                    ])
JUMP_FORWARD = dis.opname.index('JUMP_FORWARD')
try:
    STORE_DEREF = dis.opname.index('STORE_DEREF')
except ValueError:
    STORE_DEREF = None
STORE_OPS = set([STORE_NAME, STORE_FAST, STORE_GLOBAL, STORE_DEREF, STORE_MAP])
#IMPORT_STAR -> IMPORT_NAME mod ; IMPORT_STAR
#JUMP_IF_FALSE / JUMP_IF_TRUE / JUMP_FORWARD
HASJREL = set(dis.hasjrel)


def pass1(code):
    instrs = []
    i = 0
    n = len(code)
    curline = 0
    incondition = 0
    out = 0
    while i < n:
        if i >= out:
            incondition = 0
        c = code[i]
        i = i + 1
        op = ord(c)
        if op >= dis.HAVE_ARGUMENT:
            oparg = ord(code[i]) + ord(code[i + 1]) * 256
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
        if op == SET_LINENO:
            curline = oparg
        else:
            instrs.append((op, oparg, incondition, curline))
    return instrs


def scan_code(co, m=None, w=None, b=None, nested=0):
    instrs = pass1(co.co_code)
    if m is None:
        m = []
    if w is None:
        w = []
    if b is None:
        b = []
    all = []
    lastname = None
    level = -1  # import-level, same behaviour as up to Python 2.4
    for i, (op, oparg, conditional, curline) in enumerate(instrs):
        if op == IMPORT_NAME:
            if level <= 0:
                name = lastname = co.co_names[oparg]
            else:
                name = lastname = co.co_names[oparg]
            #print 'import_name', name, `lastname`, level
            m.append((name, nested, conditional, level))
        elif op == IMPORT_FROM:
            name = co.co_names[oparg]
            #print 'import_from', name, `lastname`, level,
            if level > 0 and (not lastname or lastname[-1:] == '.'):
                name = lastname + name
            else:
                name = lastname + '.' + name
            #print name
            m.append((name, nested, conditional, level))
            assert lastname is not None
        elif op == IMPORT_STAR:
            assert lastname is not None
            m.append((lastname + '.*', nested, conditional, level))
        elif op == STORE_NAME:
            if co.co_names[oparg] == "__all__":
                j = i - 1
                pop, poparg, pcondtl, pline = instrs[j]
                if pop != BUILD_LIST:
                    w.append("W: __all__ is built strangely at line %s" % pline)
                else:
                    all = []
                    while j > 0:
                        j = j - 1
                        pop, poparg, pcondtl, pline = instrs[j]
                        if pop == LOAD_CONST:
                            all.append(co.co_consts[poparg])
                        else:
                            break
        elif op in STORE_OPS:
            pass
        elif op == LOAD_CONST_level:
            # starting with Python 2.5, _each_ import is preceeded with a
            # LOAD_CONST to indicate the relative level.
            if isinstance(co.co_consts[oparg], (int, long)):
                level = co.co_consts[oparg]
        elif op == LOAD_GLOBAL:
            name = co.co_names[oparg]
            cndtl = ['', 'conditional'][conditional]
            lvl = ['top-level', 'delayed'][nested]
            if name == "__import__":
                w.append("W: %s %s __import__ hack detected at line %s" % (lvl, cndtl, curline))
            elif name == "eval":
                w.append("W: %s %s eval hack detected at line %s" % (lvl, cndtl, curline))
        elif op == EXEC_STMT:
            cndtl = ['', 'conditional'][conditional]
            lvl = ['top-level', 'delayed'][nested]
            w.append("W: %s %s exec statement detected at line %s" % (lvl, cndtl, curline))
        else:
            lastname = None

        if ctypes:
            # ctypes scanning requires a scope wider than one bytecode instruction,
            # so the code resides in a separate function for clarity.
            ctypesb, ctypesw = scan_code_for_ctypes(co, instrs, i)
            b.extend(ctypesb)
            w.extend(ctypesw)

    for c in co.co_consts:
        if isinstance(c, type(co)):
            # FIXME: "all" was not updated here nor returned. Was it the desired
            # behaviour?
            _, _, _, all_nested = scan_code(c, m, w, b, 1)
            all.extend(all_nested)
    return m, w, b, all


def scan_code_for_ctypes(co, instrs, i):
    """
    Detects ctypes dependencies, using reasonable heuristics that should
    cover most common ctypes usages; returns a tuple of two lists, one
    containing names of binaries detected as dependencies, the other containing
    warnings.
    """

    def _libFromConst(i):
        """Extracts library name from an expected LOAD_CONST instruction and
        appends it to local binaries list.
        """
        op, oparg, conditional, curline = instrs[i]
        if op == LOAD_CONST:
            soname = co.co_consts[oparg]
            b.append(soname)

    b = []

    op, oparg, conditional, curline = instrs[i]

    if op in (LOAD_GLOBAL, LOAD_NAME):
        name = co.co_names[oparg]

        if name in ("CDLL", "WinDLL"):
            # Guesses ctypes imports of this type: CDLL("library.so")

            # LOAD_GLOBAL 0 (CDLL) <--- we "are" here right now
            # LOAD_CONST 1 ('library.so')

            _libFromConst(i + 1)

        elif name == "ctypes":
            # Guesses ctypes imports of this type: ctypes.DLL("library.so")

            # LOAD_GLOBAL 0 (ctypes) <--- we "are" here right now
            # LOAD_ATTR 1 (CDLL)
            # LOAD_CONST 1 ('library.so')

            op2, oparg2, conditional2, curline2 = instrs[i + 1]
            if op2 == LOAD_ATTR:
                if co.co_names[oparg2] in ("CDLL", "WinDLL"):
                    # Fetch next, and finally get the library name
                    _libFromConst(i + 2)

        elif name in ("cdll", "windll"):
            # Guesses ctypes imports of these types:

            #  * cdll.library (only valid on Windows)

            #     LOAD_GLOBAL 0 (cdll) <--- we "are" here right now
            #     LOAD_ATTR 1 (library)

            #  * cdll.LoadLibrary("library.so")

            #     LOAD_GLOBAL              0 (cdll) <--- we "are" here right now
            #     LOAD_ATTR                1 (LoadLibrary)
            #     LOAD_CONST               1 ('library.so')

            op2, oparg2, conditional2, curline2 = instrs[i + 1]
            if op2 == LOAD_ATTR:
                if co.co_names[oparg2] != "LoadLibrary":
                    # First type
                    soname = co.co_names[oparg2] + ".dll"
                    b.append(soname)
                else:
                    # Second type, needs to fetch one more instruction
                    _libFromConst(i + 2)

    # If any of the libraries has been requested with anything different from
    # the bare filename, drop that entry and warn the user - pyinstaller would
    # need to patch the compiled pyc file to make it work correctly!

    w = []
    for bin in list(b):
        if bin != os.path.basename(bin):
            b.remove(bin)
            w.append("W: ignoring %s - ctypes imports only supported using bare filenames" % (bin,))

    return b, w


def _resolveCtypesImports(cbinaries):
    """Completes ctypes BINARY entries for modules with their full path.
    """
    from ctypes.util import find_library

    if is_unix:
        envvar = "LD_LIBRARY_PATH"
    elif is_darwin:
        envvar = "DYLD_LIBRARY_PATH"
    else:
        envvar = "PATH"

    def _setPaths():
        path = os.pathsep.join(PyInstaller.__pathex__)
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
        # Ignore annoying warnings like:
        # 'W: library kernel32.dll required via ctypes not found'
        # 'W: library coredll.dll required via ctypes not found'
        if cbin in ['coredll.dll', 'kernel32.dll']:
            continue
        ext = os.path.splitext(cbin)[1]
        # On Windows, only .dll files can be loaded.
        if os.name == "nt" and ext.lower() in [".so", ".dylib"]:
            continue
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
                text = compat.exec_command("/sbin/ldconfig", "-p")
                for L in text.strip().splitlines():
                    if cpath in L:
                        cpath = L.split("=>", 1)[1].strip()
                        assert os.path.isfile(cpath)
                        break
                else:
                    cpath = None
        if cpath is None:
            logger.warn("library %s required via ctypes not found", cbin)
        else:
            ret.append((cbin, cpath, "BINARY"))
    _restorePaths(old)
    return ret
