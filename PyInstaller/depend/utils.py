# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
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
import ctypes.util
import dis
import io
import marshal
import os
import re
import zipfile

from ..lib.modulegraph import util, modulegraph

from .. import compat
from ..compat import (is_darwin, is_unix, is_freebsd, is_py2, is_py37,
                      BYTECODE_MAGIC, PY3_BASE_MODULES,
                      exec_python_rc)
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
    # Excluded are plain 'modules' or 'submodules.ANY_NAME'.
    # The match has to be exact - start and end of string not substring.
    regex_modules = '|'.join([r'(^%s$)' % x for x in PY3_BASE_MODULES])
    regex_submod = '|'.join([r'(^%s\..*$)' % x for x in PY3_BASE_MODULES])
    regex_str = regex_modules + '|' + regex_submod
    module_filter = re.compile(regex_str)

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
                    if module_filter.match(mod.identifier):
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
                            if not is_py37:
                                # old format
                                fc.write(BYTECODE_MAGIC)
                                _write_long(fc, timestamp)
                                _write_long(fc, size)
                            else:
                                # new format - still timestamp based
                                fc.write(BYTECODE_MAGIC)
                                _write_long(fc, 0) # flags
                                _write_long(fc, timestamp)
                                _write_long(fc, size)
                            marshal.dump(mod.code, fc)
                            # Use a ZipInfo to set timestamp for deterministic build
                            info = zipfile.ZipInfo(new_name)
                            zf.writestr(info, fc.getvalue())

    except Exception as e:
        logger.error('base_library.zip could not be created!')
        raise


def scan_code_for_ctypes(co):
    binaries = []

    __recursivly_scan_code_objects_for_ctypes(co, binaries)

    # If any of the libraries has been requested with anything
    # different then the bare filename, drop that entry and warn
    # the user - pyinstaller would need to patch the compiled pyc
    # file to make it work correctly!
    binaries = set(binaries)
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
            try:
                filename = co.co_filename
            except:
                filename = 'UNKNOWN'
            logger.warning("Ignoring %s imported from %s - ctypes imports "
                           "are only supported using bare filenames",
                           binary, filename)
            binaries.remove(binary)

    binaries = _resolveCtypesImports(binaries)
    return binaries


def __recursivly_scan_code_objects_for_ctypes(co, binaries):
    # ctypes scanning requires a scope wider than one bytecode
    # instruction, so the code resides in a separate function
    # for clarity.
    binaries.extend(
        __scan_code_instruction_for_ctypes(
            util.iterate_instructions(co)))


def __scan_code_instruction_for_ctypes(instructions):
    """
    Detects ctypes dependencies, using reasonable heuristics that
    should cover most common ctypes usages; returns a tuple of two
    lists, one containing names of binaries detected as
    dependencies, the other containing warnings.
    """
    def _libFromConst():
        """Extracts library name from an expected LOAD_CONST instruction and
        appends it to local binaries list.
        """
        instruction = next(instructions)
        if instruction.opname == 'LOAD_CONST':
            soname = instruction.argval
            if isinstance(soname, str):
                return soname

    while True:
        try:
            instruction = next(instructions)
            expected_ops = ('LOAD_GLOBAL', 'LOAD_NAME')
            load_method = ('LOAD_ATTR', 'LOAD_METHOD')

            if not instruction or instruction.opname not in expected_ops:
                continue

            name = instruction.argval
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
                instruction = next(instructions)
                if instruction.opname not in load_method:
                    continue
                name = instruction.argval

            if name in ("CDLL", "WinDLL", "OleDLL", "PyDLL"):
                # Guesses ctypes imports of this type: CDLL("library.so")
                #
                #   LOAD_GLOBAL 0 (CDLL) <--- we "are" here right now
                #   LOAD_CONST 1 ('library.so')

                yield _libFromConst()

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
                instruction = next(instructions)
                if instruction.opname in load_method:
                    if instruction.argval == "LoadLibrary":
                        # Second type, needs to fetch one more instruction
                        yield _libFromConst()
                    else:
                        # First type
                        yield instruction.argval + ".dll"

            elif instruction.opname == 'LOAD_ATTR' and name in ("util",):
                # Guesses ctypes imports of these types::
                #
                #  ctypes.util.find_library('gs')
                #
                #     LOAD_GLOBAL   0 (ctypes)
                #     LOAD_ATTR     1 (util) <--- we "are" here right now
                #     LOAD_ATTR     1 (find_library)
                #     LOAD_CONST    1 ('gs')
                instruction = next(instructions)
                if instruction.opname in load_method:
                    if instruction.argval == "find_library":
                        libname = _libFromConst()
                        if libname:
                            lib = ctypes.util.find_library(libname)
                            if lib:
                                # On Windows, `find_library` may return
                                # a full pathname. See issue #1934
                                yield os.path.basename(lib)
        except StopIteration:
            break


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
    # executing ctypes.util.find_library prepending ImportTracker's
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
                if LDCONFIG_CACHE is None:
                    load_ldconfig_cache()
                if cpath in LDCONFIG_CACHE:
                    cpath = LDCONFIG_CACHE[cpath]
                    assert os.path.isfile(cpath)
                else:
                    cpath = None
        if cpath is None:
            # Skip warning message if cbin (basename of library) is ignored.
            # This prevents messages like:
            # 'W: library kernel32.dll required via ctypes not found'
            if not include_library(cbin):
                continue
            logger.warning("library %s required via ctypes not found", cbin)
        else:
            if not include_library(cpath):
                continue
            ret.append((cbin, cpath, "BINARY"))
    _restorePaths(old)
    return ret


LDCONFIG_CACHE = None  # cache the output of `/sbin/ldconfig -p`

def load_ldconfig_cache():
    """
    Create a cache of the `ldconfig`-output to call it only once.
    It contains thousands of libraries and running it on every dynlib
    is expensive.
    """
    global LDCONFIG_CACHE

    if LDCONFIG_CACHE is not None:
        return

    from distutils.spawn import find_executable
    ldconfig = find_executable('ldconfig')
    if ldconfig is None:
        # If `lsconfig` is not found in $PATH, search it in some fixed
        # directories. Simply use a second call instead of fiddling
        # around with checks for empty env-vars and string-concat.
        ldconfig = find_executable('ldconfig',
                                   '/usr/sbin:/sbin:/usr/bin:/usr/sbin')

        # if we still couldn't find 'ldconfig' command
        if ldconfig is None:
            LDCONFIG_CACHE = {}
            return

    if is_freebsd:
        # This has a quite different format than other Unixes
        # [vagrant@freebsd-10 ~]$ ldconfig -r
        # /var/run/ld-elf.so.hints:
        #     search directories: /lib:/usr/lib:/usr/lib/compat:...
        #     0:-lgeom.5 => /lib/libgeom.so.5
        #   184:-lpython2.7.1 => /usr/local/lib/libpython2.7.so.1
        text = compat.exec_command(ldconfig, '-r')
        text = text.strip().splitlines()[2:]
        pattern = re.compile(r'^\s+\d+:-l(.+?)((\.\d+)+) => (\S+)')
        pattern = re.compile(r'^\s+\d+:-l(\S+)(\s.*)? => (\S+)')
    else:
        # Skip first line of the library list because it is just
        # an informative line and might contain localized characters.
        # Example of first line with local cs_CZ.UTF-8:
        #$ /sbin/ldconfig -p
        #V keši „/etc/ld.so.cache“ nalezeno knihoven: 2799
        #      libzvbi.so.0 (libc6,x86-64) => /lib64/libzvbi.so.0
        #      libzvbi-chains.so.0 (libc6,x86-64) => /lib64/libzvbi-chains.so.0
        text = compat.exec_command(ldconfig, '-p')
        text = text.strip().splitlines()[1:]
        pattern = re.compile(r'^\s+(\S+)(\s.*)? => (\S+)')

    LDCONFIG_CACHE = {}
    for line in text:
        # :fixme: this assumes libary names do not contain whitespace
        m = pattern.match(line)
        path = m.groups()[-1]
        if is_freebsd:
            # Insert `.so` at the end of the lib's basename. soname
            # and filename may have (different) trailing versions. We
            # assume the `.so` in the filename to mark the end of the
            # lib's basename.
            bname = os.path.basename(path).split('.so', 1)[0]
            name = 'lib' + m.group(1)
            assert name.startswith(bname)
            name = bname + '.so' + name[len(bname):]
        else:
            name = m.group(1)
        # ldconfig may know about several versions of the same lib,
        # e.g. differents arch, different libc, etc. Use the first
        # entry.
        if not name in LDCONFIG_CACHE:
            LDCONFIG_CACHE[name] = path


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
