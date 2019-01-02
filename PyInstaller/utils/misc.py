#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
This module is for the miscellaneous routines which do not fit somewhere else.
"""

import glob
import os
import pprint
import py_compile
import sys

from PyInstaller import log as logging
from PyInstaller.compat import BYTECODE_MAGIC, is_py2, text_read_mode

logger = logging.getLogger(__name__)


def dlls_in_subdirs(directory):
    """Returns a list *.dll, *.so, *.dylib in given directories and subdirectories."""
    filelist = []
    for root, dirs, files in os.walk(directory):
        filelist.extend(dlls_in_dir(root))
    return filelist


def dlls_in_dir(directory):
    """Returns a list of *.dll, *.so, *.dylib in given directory."""
    return files_in_dir(directory, ["*.so", "*.dll", "*.dylib"])


def files_in_dir(directory, file_patterns=[]):
    """Returns a list of files which match a pattern in given directory."""
    files = []
    for file_pattern in file_patterns:
        files.extend(glob.glob(os.path.join(directory, file_pattern)))
    return files


def get_unicode_modules():
    """
    Try importing codecs and encodings to include unicode support
    in created binary.
    """
    modules = []
    try:
        # `codecs` depends on `encodings` and this is then included.
        import codecs
        modules.append('codecs')
    except ImportError:
        logger.error("Cannot detect modules 'codecs'.")

    return modules


def get_path_to_toplevel_modules(filename):
    """
    Return the path to top-level directory that contains Python modules.

    It will look in parent directories for __init__.py files. The first parent
    directory without __init__.py is the top-level directory.

    Returned directory might be used to extend the PYTHONPATH.
    """
    curr_dir = os.path.dirname(os.path.abspath(filename))
    pattern = '__init__.py'

    # Try max. 10 levels up.
    try:
        for i in range(10):
            files = set(os.listdir(curr_dir))
            # 'curr_dir' is still not top-leve go to parent dir.
            if pattern in files:
                curr_dir = os.path.dirname(curr_dir)
            # Top-level dir found - return it.
            else:
                return curr_dir
    except IOError:
        pass
    # No top-level directory found or any error.
    return None


def mtime(fnm):
    try:
        # TODO: explain why this doesn't use os.path.getmtime() ?
        #       - It is probably not used because it returns fload and not int.
        return os.stat(fnm)[8]
    except:
        return 0


def compile_py_files(toc, workpath):
    """
    Given a TOC or equivalent list of tuples, generates all the required
    pyc/pyo files, writing in a local directory if required, and returns the
    list of tuples with the updated pathnames.

    In the old system using ImpTracker, the generated TOC of "pure" modules
    already contains paths to nm.pyc or nm.pyo and it is only necessary
    to check that these files are not older than the source.
    In the new system using ModuleGraph, the path given is to nm.py
    and we do not know if nm.pyc/.pyo exists. The following logic works
    with both (so if at some time modulegraph starts returning filenames
    of .pyc, it will cope).
    """

    # For those modules that need to be rebuilt, use the build directory
    # PyInstaller creates during the build process.
    basepath = os.path.join(workpath, "localpycos")

    # Copy everything from toc to this new TOC, possibly unchanged.
    new_toc = []
    for (nm, fnm, typ) in toc:
        # Keep unrelevant items unchanged.
        if typ != 'PYMODULE':
            new_toc.append((nm, fnm, typ))
            continue

        if fnm.endswith('.py') :
            # we are given a source path, determine the object path if any
            src_fnm = fnm
            # assume we want pyo only when now running -O or -OO
            obj_fnm = src_fnm + ('o' if sys.flags.optimize else 'c')
            if not os.path.exists(obj_fnm) :
                # alas that one is not there so assume the other choice
                obj_fnm = src_fnm + ('c' if sys.flags.optimize else 'o')
        else:
            # fnm is not "name.py" so assume we are given name.pyc/.pyo
            obj_fnm = fnm # take that namae to be the desired object
            src_fnm = fnm[:-1] # drop the 'c' or 'o' to make a source name

        # We need to perform a build ourselves if obj_fnm doesn't exist,
        # or if src_fnm is newer than obj_fnm, or if obj_fnm was created
        # by a different Python version.
        # TODO: explain why this does read()[:4] (reading all the file)
        # instead of just read(4)? Yes for many a .pyc file, it is all
        # in one sector so there's no difference in I/O but still it
        # seems inelegant to copy it all then subscript 4 bytes.
        needs_compile = mtime(src_fnm) > mtime(obj_fnm)
        if not needs_compile:
            with open(obj_fnm, 'rb') as fh:
                needs_compile = fh.read()[:4] != BYTECODE_MAGIC
        if needs_compile:
            try:
                # TODO: there should be no need to repeat the compile,
                # because ModuleGraph does a compile and stores the result
                # in the .code member of the graph node. Should be possible
                # to get the node and write the code to obj_fnm
                py_compile.compile(src_fnm, obj_fnm)
                logger.debug("compiled %s", src_fnm)
            except IOError:
                # If we're compiling on a system directory, probably we don't
                # have write permissions; thus we compile to a local directory
                # and change the TOC entry accordingly.
                ext = os.path.splitext(obj_fnm)[1]

                if "__init__" not in obj_fnm:
                    # If it's a normal module, use last part of the qualified
                    # name as module name and the first as leading path
                    leading, mod_name = nm.split(".")[:-1], nm.split(".")[-1]
                else:
                    # In case of a __init__ module, use all the qualified name
                    # as leading path and use "__init__" as the module name
                    leading, mod_name = nm.split("."), "__init__"

                leading = os.path.join(basepath, *leading)

                if not os.path.exists(leading):
                    os.makedirs(leading)

                obj_fnm = os.path.join(leading, mod_name + ext)
                # TODO see above regarding read()[:4] versus read(4)
                needs_compile = mtime(src_fnm) > mtime(obj_fnm)
                if not needs_compile:
                    with open(obj_fnm, 'rb') as fh:
                        needs_compile = fh.read()[:4] != BYTECODE_MAGIC
                if needs_compile:
                    # TODO see above todo regarding using node.code
                    py_compile.compile(src_fnm, obj_fnm)
                    logger.debug("compiled %s", src_fnm)
        # if we get to here, obj_fnm is the path to the compiled module nm.py
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
    if is_py2:
        import codecs
        f = codecs.open(filename, 'w', encoding='utf-8')
    else:
        f = open(filename, 'w', encoding='utf-8')
    with f:
        pprint.pprint(data, f)


def load_py_data_struct(filename):
    """
    Load data saved as python code and interpret that code.
    :param filename:
    :return:
    """
    if is_py2:
        import codecs
        f = codecs.open(filename, text_read_mode, encoding='utf-8')
    else:
        f = open(filename, text_read_mode, encoding='utf-8')
    with f:
        # Binding redirects are stored as a named tuple, so bring the namedtuple
        # class into scope for parsing the TOC.
        from ..depend.bindepend import BindingRedirect

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
    # Ignore the last component in module name and get really just
    # parent, grand parent, grandgrand parent, etc.
    for pkg in full_modname.split('.')[0:-1]:
        # Ensure first item does not start with dot '.'
        prefix += '.' + pkg if prefix else pkg
        parents.append(prefix)
    return parents
