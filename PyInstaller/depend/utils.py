# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


"""
Utility functions related to analyzing/bundling dependencies.
"""

import ctypes
import ctypes.util
import io
import marshal
import os
import re
import struct
import zipfile

from ..exceptions import ExecCommandFailed
from ..lib.modulegraph import util, modulegraph

from .. import compat
from ..compat import (is_darwin, is_unix, is_freebsd, is_openbsd, is_py37,
                      BYTECODE_MAGIC, PY3_BASE_MODULES)
from .dylib import include_library
from .. import log as logging

try:
    # source_hash only exists in Python 3.7
    from importlib.util import source_hash as importlib_source_hash
except ImportError:
    pass

logger = logging.getLogger(__name__)


# TODO find out if modules from base_library.zip could be somehow bundled into the .exe file.
def create_py3_base_library(libzip_filename, graph):
    """
    Package basic Python modules into .zip file. The .zip file with basic
    modules is necessary to have on PYTHONPATH for initializing libpython3
    in order to run the frozen executable with Python 3.
    """
    # Import strip_paths_in_code locally to avoid cyclic import between
    # building.utils and depend.utils (this module); building.utils
    # imports depend.bindepend, which in turn imports depend.utils.
    from ..building.utils import strip_paths_in_code
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
            # Sort the graph nodes by identifier to ensure repeatable builds
            graph_nodes = list(graph.flatten())
            graph_nodes.sort(key=lambda item: item.identifier)
            for mod in graph_nodes:
                if type(mod) in (modulegraph.SourceModule,
                                 modulegraph.Package,
                                 modulegraph.CompiledModule):
                    # Bundling just required modules.
                    if module_filter.match(mod.identifier):
                        st = os.stat(mod.filename)
                        timestamp = int(st.st_mtime)
                        size = st.st_size & 0xFFFFFFFF
                        # Name inside the archive. The ZIP format
                        # specification requires forward slashes as
                        # directory separator.
                        # TODO use .pyo suffix if optimize flag is enabled.
                        if type(mod) is modulegraph.Package:
                            new_name = mod.identifier.replace('.', '/') \
                                + '/__init__.pyc'
                        else:
                            new_name = mod.identifier.replace('.', '/') \
                                + '.pyc'

                        # Write code to a file.
                        # This code is similar to py_compile.compile().
                        with io.BytesIO() as fc:
                            # Prepare all data in byte stream file-like object.
                            fc.write(BYTECODE_MAGIC)
                            if is_py37:
                                # Additional bitfield according to PEP 552
                                # 0b01 means hash based but don't check the hash
                                fc.write(struct.pack('<I', 0b01))
                                with open(mod.filename, 'rb') as fs:
                                    source_bytes = fs.read()
                                source_hash = importlib_source_hash(source_bytes)
                                fc.write(source_hash)
                            else:
                                fc.write(struct.pack('<II', timestamp, size))
                            code = strip_paths_in_code(mod.code)  # Strip paths
                            marshal.dump(code, fc)
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
        try:
            # There is an issue with find_library() where it can run into
            # errors trying to locate the library. See #5734.
            cpath = find_library(os.path.splitext(cbin)[0])
        except FileNotFoundError:
            # In these cases, find_library() should return None.
            cpath = None
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
    It contains thousands of libraries and running it on every dylib
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

    if is_freebsd or is_openbsd:
        # This has a quite different format than other Unixes
        # [vagrant@freebsd-10 ~]$ ldconfig -r
        # /var/run/ld-elf.so.hints:
        #     search directories: /lib:/usr/lib:/usr/lib/compat:...
        #     0:-lgeom.5 => /lib/libgeom.so.5
        #   184:-lpython2.7.1 => /usr/local/lib/libpython2.7.so.1
        ldconfig_arg = '-r'
        splitlines_count = 2
        pattern = re.compile(r'^\s+\d+:-l(\S+)(\s.*)? => (\S+)')
    else:
        # Skip first line of the library list because it is just
        # an informative line and might contain localized characters.
        # Example of first line with local cs_CZ.UTF-8:
        #$ /sbin/ldconfig -p
        #V keši „/etc/ld.so.cache“ nalezeno knihoven: 2799
        #      libzvbi.so.0 (libc6,x86-64) => /lib64/libzvbi.so.0
        #      libzvbi-chains.so.0 (libc6,x86-64) => /lib64/libzvbi-chains.so.0
        ldconfig_arg = '-p'
        splitlines_count = 1
        pattern = re.compile(r'^\s+(\S+)(\s.*)? => (\S+)')

    try:
        text = compat.exec_command(ldconfig, ldconfig_arg)
    except ExecCommandFailed:
        logger.warning("Failed to execute ldconfig. Disabling LD cache.")
        LDCONFIG_CACHE = {}
        return

    text = text.strip().splitlines()[splitlines_count:]

    LDCONFIG_CACHE = {}
    for line in text:
        # :fixme: this assumes libary names do not contain whitespace
        m = pattern.match(line)

        # Sanitize away any abnormal lines of output.
        if m is None:
            # Warn about it then skip the rest of this iteration.
            if re.search("Cache generated by:", line):
                # See #5540. This particular line is harmless.
                pass
            else:
                logger.warning(
                    "Unrecognised line of output %r from ldconfig", line)
            continue

        path = m.groups()[-1]
        if is_freebsd or is_openbsd:
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
