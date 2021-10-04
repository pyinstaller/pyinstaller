#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
This module contains miscellaneous functions that do not fit anywhere else.
"""

import glob
import os
import pprint
import py_compile
import sys
import codecs
import re
import tokenize
import io

from PyInstaller import log as logging
from PyInstaller.compat import BYTECODE_MAGIC, is_win

logger = logging.getLogger(__name__)


def dlls_in_subdirs(directory):
    """
    Returns a list *.dll, *.so, *.dylib in the given directory and its subdirectories.
    """
    filelist = []
    for root, dirs, files in os.walk(directory):
        filelist.extend(dlls_in_dir(root))
    return filelist


def dlls_in_dir(directory):
    """
    Returns a list of *.dll, *.so, *.dylib in the given directory.
    """
    return files_in_dir(directory, ["*.so", "*.dll", "*.dylib"])


def files_in_dir(directory, file_patterns=[]):
    """
    Returns a list of files in the given directory that match the given pattern.
    """
    files = []
    for file_pattern in file_patterns:
        files.extend(glob.glob(os.path.join(directory, file_pattern)))
    return files


def get_unicode_modules():
    """
    Try importing modules required for unicode support in the frozen application.
    """
    modules = []
    try:
        # `codecs` depends on `encodings`, so the latter are included automatically.
        import codecs  # noqa: F401
        modules.append('codecs')
    except ImportError:
        logger.error("Cannot detect modules 'codecs'.")

    return modules


def get_path_to_toplevel_modules(filename):
    """
    Return the path to top-level directory that contains Python modules.

    It will look in parent directories for __init__.py files. The first parent directory without __init__.py is the
    top-level directory.

    Returned directory might be used to extend the PYTHONPATH.
    """
    curr_dir = os.path.dirname(os.path.abspath(filename))
    pattern = '__init__.py'

    # Try max. 10 levels up.
    try:
        for i in range(10):
            files = set(os.listdir(curr_dir))
            # 'curr_dir' is still not top-level; go to parent dir.
            if pattern in files:
                curr_dir = os.path.dirname(curr_dir)
            # Top-level dir found; return it.
            else:
                return curr_dir
    except IOError:
        pass
    # No top-level directory found, or error was encountered.
    return None


def mtime(fnm):
    try:
        # TODO: explain why this does not use os.path.getmtime() ?
        #       - It is probably not used because it returns float and not int.
        return os.stat(fnm)[8]
    except Exception:
        return 0


def compile_py_files(toc, workpath):
    """
    Given a TOC or equivalent list of tuples, generates all the required pyc/pyo files, writing in a local directory
    if required, and returns the list of tuples with the updated pathnames.

    In the old system using ImpTracker, the generated TOC of "pure" modules already contains paths to nm.pyc or
    nm.pyo and it is only necessary to check that these files are not older than the source. In the new system using
    ModuleGraph, the path given is to nm.py and we do not know if nm.pyc/.pyo exists. The following logic works with
    both (so if at some time modulegraph starts returning filenames of .pyc, it will cope).
    """

    # For those modules that need to be rebuilt, use the build directory PyInstaller creates during the build process.
    basepath = os.path.join(workpath, "localpycos")

    # Copy everything from toc to this new TOC, possibly unchanged.
    new_toc = []
    for (nm, fnm, typ) in toc:
        # Keep irrelevant items unchanged.
        if typ != 'PYMODULE':
            new_toc.append((nm, fnm, typ))
            continue

        if fnm in ('-', None):
            # If fmn represents a namespace then skip
            continue

        if fnm.endswith('.py'):
            # We are given a source path, determine the object path, if any.
            src_fnm = fnm
            # Assume we want pyo only when now running -O or -OO
            obj_fnm = src_fnm + ('o' if sys.flags.optimize else 'c')
            if not os.path.exists(obj_fnm):
                # Alas that one is not there so assume the other choice.
                obj_fnm = src_fnm + ('c' if sys.flags.optimize else 'o')
        else:
            # fnm is not "name.py", so assume we are given name.pyc/.pyo
            obj_fnm = fnm  # take that name to be the desired object
            src_fnm = fnm[:-1]  # drop the 'c' or 'o' to make a source name

        # We need to perform a build ourselves if obj_fnm does not exist, or if src_fnm is newer than obj_fnm, or if
        # obj_fnm was created by a different Python version.

        # TODO: explain why this does read()[:4] (reading all the file) instead of just read(4)? Yes for many a .pyc
        #       file, it is all in one sector so there is no difference in I/O, but still it seems inelegant to copy it
        #       all then subscript 4 bytes.
        needs_compile = mtime(src_fnm) > mtime(obj_fnm)
        if not needs_compile:
            with open(obj_fnm, 'rb') as fh:
                needs_compile = fh.read()[:4] != BYTECODE_MAGIC
        if needs_compile:
            try:
                # TODO: there should be no need to repeat the compile, because ModuleGraph does a compile and stores the
                #       result in the .code member of the graph node. Should be possible to get the node and write the
                #       code to obj_fnm.
                py_compile.compile(src_fnm, obj_fnm)
                logger.debug("compiled %s", src_fnm)
            except IOError:
                # If we are compiling in a system directory, we probably do not have write permissions; thus we compile
                # to a local directory and change the TOC entry accordingly.
                ext = os.path.splitext(obj_fnm)[1]

                if "__init__" not in obj_fnm:
                    # If it is a normal module, use the last part of the qualified name as the module name and the first
                    # part as the leading path.
                    leading, mod_name = nm.split(".")[:-1], nm.split(".")[-1]
                else:
                    # In case of an __init__ module, use all the qualified name as the leading path and use "__init__"
                    # as the module name.
                    leading, mod_name = nm.split("."), "__init__"

                leading = os.path.join(basepath, *leading)

                if not os.path.exists(leading):
                    os.makedirs(leading)

                obj_fnm = os.path.join(leading, mod_name + ext)
                # TODO: see above TODO regarding read()[:4] versus read(4).
                needs_compile = mtime(src_fnm) > mtime(obj_fnm)
                if not needs_compile:
                    with open(obj_fnm, 'rb') as fh:
                        needs_compile = fh.read()[:4] != BYTECODE_MAGIC
                if needs_compile:
                    # TODO: see above TODO regarding using node.code.
                    py_compile.compile(src_fnm, obj_fnm)
                    logger.debug("compiled %s", src_fnm)
        # If we get to here, obj_fnm is the path to the compiled module nm.py
        new_toc.append((nm, obj_fnm, typ))

    return new_toc


def save_py_data_struct(filename, data):
    """
    Save data into text file as Python data structure.
    :param filename:
    :param data:
    :return:
    """
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    with open(filename, 'w', encoding='utf-8') as f:
        pprint.pprint(data, f)


def load_py_data_struct(filename):
    """
    Load data saved as python code and interpret that code.
    :param filename:
    :return:
    """
    with open(filename, 'r', encoding='utf-8') as f:
        # Binding redirects are stored as a named tuple, so bring the namedtuple class into scope for parsing the TOC.
        from PyInstaller.depend.bindepend import BindingRedirect  # noqa: F401

        if is_win:
            # import versioninfo so that VSVersionInfo can parse correctly.
            from PyInstaller.utils.win32 import versioninfo  # noqa: F401

        return eval(f.read())


def absnormpath(apath):
    return os.path.abspath(os.path.normpath(apath))


def module_parent_packages(full_modname):
    """
    Return list of parent package names.
        'aaa.bb.c.dddd' ->  ['aaa', 'aaa.bb', 'aaa.bb.c']
    :param full_modname: Full name of a module.
    :return: List of parent module names.
    """
    prefix = ''
    parents = []
    # Ignore the last component in module name and get really just parent, grandparent, great grandparent, etc.
    for pkg in full_modname.split('.')[0:-1]:
        # Ensure that first item does not start with dot '.'
        prefix += '.' + pkg if prefix else pkg
        parents.append(prefix)
    return parents


def is_file_qt_plugin(filename):
    """
    Check if the given file is a Qt plugin file.
    :param filename: Full path to file to check.
    :return: True if given file is a Qt plugin file, False if not.
    """

    # Check the file contents; scan for QTMETADATA string. The scan is based on the brute-force Windows codepath of
    # findPatternUnloaded() from qtbase/src/corelib/plugin/qlibrary.cpp in Qt5.
    with open(filename, 'rb') as fp:
        fp.seek(0, os.SEEK_END)
        end_pos = fp.tell()

        SEARCH_CHUNK_SIZE = 8192
        QTMETADATA_MAGIC = b'QTMETADATA '

        magic_offset = -1
        while end_pos >= len(QTMETADATA_MAGIC):
            start_pos = max(end_pos - SEARCH_CHUNK_SIZE, 0)
            chunk_size = end_pos - start_pos
            # Is the remaining chunk large enough to hold the pattern?
            if chunk_size < len(QTMETADATA_MAGIC):
                break
            # Read and scan the chunk
            fp.seek(start_pos, os.SEEK_SET)
            buf = fp.read(chunk_size)
            pos = buf.rfind(QTMETADATA_MAGIC)
            if pos != -1:
                magic_offset = start_pos + pos
                break
            # Adjust search location for next chunk; ensure proper overlap.
            end_pos = start_pos + len(QTMETADATA_MAGIC) - 1
        if magic_offset == -1:
            return False

        return True


BOM_MARKERS_TO_DECODERS = {
    codecs.BOM_UTF32_LE: codecs.utf_32_le_decode,
    codecs.BOM_UTF32_BE: codecs.utf_32_be_decode,
    codecs.BOM_UTF32: codecs.utf_32_decode,
    codecs.BOM_UTF16_LE: codecs.utf_16_le_decode,
    codecs.BOM_UTF16_BE: codecs.utf_16_be_decode,
    codecs.BOM_UTF16: codecs.utf_16_decode,
    codecs.BOM_UTF8: codecs.utf_8_decode,
}
BOM_RE = re.compile(rb"\A(%s)?(.*)" % b"|".join(map(re.escape, BOM_MARKERS_TO_DECODERS)), re.DOTALL)


def decode(raw: bytes):
    """
    Decode bytes to string, respecting and removing any byte-order marks if present, or respecting but not removing any
    PEP263 encoding comments (# encoding: cp1252).
    """
    bom, raw = BOM_RE.match(raw).groups()
    if bom:
        return BOM_MARKERS_TO_DECODERS[bom](raw)[0]

    encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
    return raw.decode(encoding)
